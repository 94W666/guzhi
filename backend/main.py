"""FastAPI application — Multi-Dimensional Fund Analysis Platform."""

from datetime import date
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os

from contextlib import asynccontextmanager

from database import init_db, get_db
from models import Fund, Holding, FundNav
from calculator.metrics import (
    compute_all_metrics,
    max_drawdown,
    annualized_return,
    volatility,
    sharpe_ratio,
    fund_pe_ratio,
    sortino_ratio,
    calmar_ratio,
    win_rate,
    _period_cutoff_date,
)
from scraper.fund_nav import ensure_nav_data
from scraper.fund_holdings import fetch_holdings, save_holdings_to_db
from calculator.metrics import dca_backtest
from calculator.commentary import generate_commentary

# Track funds where we already tried (and failed) to fetch holdings
_holdings_fetch_attempted = set()

# Fund list cache — 避免每次搜索都请求东方财富
_fund_list_cache: dict = {"data": None, "ts": 0}
_FUND_LIST_CACHE_TTL = 3600  # 1小时

def _cached_fund_list():
    import time
    now = time.time()
    if _fund_list_cache["data"] is not None and (now - _fund_list_cache["ts"]) < _FUND_LIST_CACHE_TTL:
        return _fund_list_cache["data"]
    from scraper.fund_list import fetch_fund_list as _fetch
    data = _fetch("all")
    if data:
        _fund_list_cache["data"] = data
        _fund_list_cache["ts"] = now
    return data


# DCA 结果缓存 — 同一基金+参数当天只算一次
_dca_cache: dict = {}

def _cached_dca(code, amount, years, db):
    from datetime import date as _date
    today_key = _date.today().isoformat()
    cache_key = f"{code}:{amount}:{years}"
    entry = _dca_cache.get(cache_key)
    if entry and entry["day"] == today_key:
        return entry["data"]
    # Compute fresh
    from calculator.metrics import dca_backtest
    fund = db.query(Fund).filter(Fund.code == code).first()
    if not fund:
        return None
    ensure_nav_data(code)
    nav_records = db.query(FundNav).filter(FundNav.fund_id == fund.id).order_by(FundNav.nav_date.asc()).all()
    nav_list = [{"nav_date": n.nav_date, "unit_nav": n.unit_nav, "cumulative_nav": n.cumulative_nav, "daily_return": n.daily_return} for n in nav_records]
    if not nav_list:
        return None
    result = dca_backtest(nav_list, amount, years)
    _dca_cache[cache_key] = {"day": today_key, "data": result}
    return result


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Fund Analyzer",
    description="Multi-dimensional fund analysis: max drawdown, Sharpe ratio, P/E, volatility, and more",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Static file serving (dashboard)
# ---------------------------------------------------------------------------

static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def serve_dashboard():
    return FileResponse(os.path.join(static_dir, "index.html"))


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "Fund Analyzer"}


# ---------------------------------------------------------------------------
# Fund list & search
# ---------------------------------------------------------------------------

@app.get("/api/funds")
def list_funds(db: Session = Depends(get_db)):
    """List all funds in the database with basic info."""
    funds = db.query(Fund).all()
    return [
        {
            "id": f.id,
            "code": f.code,
            "name": f.name,
            "fund_type": f.fund_type,
            "tracking_index": f.tracking_index,
            "scale": f.scale,
        }
        for f in funds
    ]


@app.get("/api/funds/search")
def search_fund(q: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    """Search for funds by code or name.

    Returns a list of matching funds from DB and Eastmoney.
    Auto-saves only exact code matches.
    """
    results = []

    # 1. Search in DB
    db_funds = db.query(Fund).filter(
        Fund.code.contains(q) | Fund.name.contains(q)
    ).all()
    seen_codes = set()
    for f in db_funds:
        seen_codes.add(f.code)
        results.append({
            "code": f.code,
            "name": f.name,
            "fund_type": f.fund_type,
            "source": "database",
        })

    # 2. Search Eastmoney (search all fund types directly)
    from scraper.fund_list import fetch_fund_list, save_to_db as save_fund_list

    def _find_all_in_list(funds, query):
        """Find all funds matching by code or name."""
        matches = []
        for f in funds:
            code = f.get("code", "")
            name = f.get("name", "")
            if query.lower() in code.lower() or query.lower() in name.lower():
                matches.append(f)
        return matches

    all_funds = _cached_fund_list()
    if all_funds:
        matches = _find_all_in_list(all_funds, q)
        for m in matches:
            if m["code"] not in seen_codes:
                seen_codes.add(m["code"])
                results.append({
                    "code": m["code"],
                    "name": m["name"],
                    "fund_type": m.get("fund_type", "OTHER"),
                    "source": "eastmoney",
                })

        # Auto-save exact code match (regardless of how many name-matches)
        exact = next((m for m in matches if m["code"] == q), None)
        if exact:
            save_fund_list([exact])
        elif q.isdigit() and len(q) == 6:
            # Fallback: try pingzhongdata for exact 6-digit code lookup
            # (ranking API only covers top 10000 funds)
            from scraper.fund_nav import fetch_fund_name
            name = fetch_fund_name(q)
            if name:
                fund_info = {"code": q, "name": name, "fund_type": "OTHER"}
                save_fund_list([fund_info])
                if q not in seen_codes:
                    results.append({
                        "code": q, "name": name,
                        "fund_type": "OTHER", "source": "eastmoney",
                    })

    return {"query": q, "count": len(results), "results": results}


# ---------------------------------------------------------------------------
# Fund detail
# ---------------------------------------------------------------------------

@app.get("/api/funds/{code}")
def fund_detail(code: str, db: Session = Depends(get_db)):
    """Get fund detail with all metrics and holdings summary.

    Auto-discovers funds from Eastmoney if not yet in the database.
    """
    fund = db.query(Fund).filter(Fund.code == code).first()
    if not fund:
        # Auto-discover from Eastmoney
        from scraper.fund_list import fetch_fund_list, save_to_db as save_fund_list

        matched = None
        all_funds = _cached_fund_list()
        if all_funds:
            for f in all_funds:
                if f.get("code") == code:
                    matched = f
                    break

        if not matched:
            # Fallback: pingzhongdata (covers funds outside ranking top 10000)
            from scraper.fund_nav import fetch_fund_name
            name = fetch_fund_name(code)
            if name:
                matched = {"code": code, "name": name, "fund_type": "OTHER"}

        if matched:
            save_fund_list([matched])
            fund = db.query(Fund).filter(Fund.code == code).first()

    if not fund:
        raise HTTPException(status_code=404, detail=f"Fund '{code}' not found")

    # Ensure NAV data exists
    nav_count = ensure_nav_data(code)

    # Ensure holdings exist (only try once per fund per session)
    holding_count = db.query(Holding).filter(Holding.fund_id == fund.id).count()
    if holding_count == 0 and code not in _holdings_fetch_attempted:
        _holdings_fetch_attempted.add(code)
        try:
            result = fetch_holdings(code)
            if result:
                holdings_data, report_date = result
                save_holdings_to_db(fund.id, holdings_data, report_date)
        except Exception:
            pass  # holdings fetch is best-effort

    # Load NAV history
    nav_records = (
        db.query(FundNav)
        .filter(FundNav.fund_id == fund.id)
        .order_by(FundNav.nav_date.asc())
        .all()
    )

    nav_list = [
        {
            "nav_date": n.nav_date,
            "unit_nav": n.unit_nav,
            "cumulative_nav": n.cumulative_nav,
            "daily_return": n.daily_return,
        }
        for n in nav_records
    ]

    # Compute metrics
    metrics = compute_all_metrics(nav_list) if nav_list else {}

    # Load current holdings
    holdings = db.query(Holding).filter(Holding.fund_id == fund.id).all()

    return {
        "fund": {
            "id": fund.id,
            "code": fund.code,
            "name": fund.name,
            "fund_type": fund.fund_type,
            "tracking_index": fund.tracking_index,
            "scale": fund.scale,
        },
        "metrics": metrics,
        "holdings": [
            {
                "stock_code": h.stock_code,
                "stock_name": h.stock_name,
                "weight": h.weight,
                "report_date": h.report_date.isoformat(),
            }
            for h in holdings
        ],
        "data_summary": {
            "nav_records": nav_count,
            "holding_count": len(holdings),
            "nav_start": nav_list[0]["nav_date"].isoformat() if nav_list else None,
            "nav_end": nav_list[-1]["nav_date"].isoformat() if nav_list else None,
        },
    }


# ---------------------------------------------------------------------------
# NAV history
# ---------------------------------------------------------------------------

@app.get("/api/funds/{code}/nav-history")
def fund_nav_history(
    code: str,
    period: str = Query("all", pattern="^(1y|3y|5y|ytd|all)$"),
    db: Session = Depends(get_db),
):
    """Get NAV history for a fund. Query params: period=1y|3y|5y|ytd|all."""
    fund = db.query(Fund).filter(Fund.code == code).first()
    if not fund:
        raise HTTPException(status_code=404, detail=f"Fund '{code}' not found")

    ensure_nav_data(code)

    cutoff = _period_cutoff_date(period)

    query = db.query(FundNav).filter(FundNav.fund_id == fund.id)
    if cutoff:
        query = query.filter(FundNav.nav_date >= cutoff)
    nav_records = query.order_by(FundNav.nav_date.asc()).all()

    nav_list = [
        {
            "nav_date": n.nav_date.isoformat(),
            "unit_nav": n.unit_nav,
            "cumulative_nav": n.cumulative_nav,
            "daily_return": n.daily_return,
        }
        for n in nav_records
    ]

    return {"fund_code": code, "period": period, "count": len(nav_list), "data": nav_list}


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

@app.get("/api/funds/{code}/metrics")
def fund_metrics(
    code: str,
    period: str = Query("1y", pattern="^(1y|3y|5y|all)$"),
    db: Session = Depends(get_db),
):
    """Get computed metrics for a fund."""
    fund = db.query(Fund).filter(Fund.code == code).first()
    if not fund:
        raise HTTPException(status_code=404, detail=f"Fund '{code}' not found")

    ensure_nav_data(code)

    cutoff = _period_cutoff_date(period)

    query = db.query(FundNav).filter(FundNav.fund_id == fund.id)
    if cutoff:
        query = query.filter(FundNav.nav_date >= cutoff)
    nav_records = query.order_by(FundNav.nav_date.asc()).all()

    nav_list = [
        {
            "nav_date": n.nav_date,
            "unit_nav": n.unit_nav,
            "cumulative_nav": n.cumulative_nav,
            "daily_return": n.daily_return,
        }
        for n in nav_records
    ]

    if not nav_list:
        raise HTTPException(status_code=404, detail="No NAV data available")

    metrics = compute_all_metrics(nav_list)

    # Add PE data (cached, parallel)
    pe_data = fund_pe_ratio(code)
    metrics["pe_ratio"] = pe_data

    return {
        "fund_code": code,
        "fund_name": fund.name,
        "metrics": metrics,
    }


# ---------------------------------------------------------------------------
# Holdings
# ---------------------------------------------------------------------------

@app.get("/api/funds/{code}/holdings")
def fund_holdings(code: str, db: Session = Depends(get_db)):
    """Get current holdings for a fund."""
    fund = db.query(Fund).filter(Fund.code == code).first()
    if not fund:
        raise HTTPException(status_code=404, detail=f"Fund '{code}' not found")

    # Ensure holdings exist
    holdings = db.query(Holding).filter(Holding.fund_id == fund.id).all()
    if not holdings:
        try:
            result = fetch_holdings(code)
            if result:
                holdings_data, report_date = result
                save_holdings_to_db(fund.id, holdings_data, report_date)
                holdings = db.query(Holding).filter(Holding.fund_id == fund.id).all()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Failed to fetch holdings: {e}")

    return [
        {
            "stock_code": h.stock_code,
            "stock_name": h.stock_name,
            "weight": h.weight,
            "report_date": h.report_date.isoformat(),
        }
        for h in holdings
    ]


# ---------------------------------------------------------------------------
# DCA Backtest
# ---------------------------------------------------------------------------

@app.get("/api/funds/{code}/dca")
def fund_dca(
    code: str,
    amount: float = Query(1000.0, ge=100),
    years: int = Query(3, ge=1, le=10),
    db: Session = Depends(get_db),
):
    """Simulate monthly dollar-cost averaging backtest (cached per day)."""
    fund = db.query(Fund).filter(Fund.code == code).first()
    if not fund:
        raise HTTPException(status_code=404, detail=f"Fund '{code}' not found")

    result = _cached_dca(code, amount, years, db)
    if not result:
        raise HTTPException(status_code=404, detail="Not enough NAV data for DCA backtest")

    return {
        "fund_code": code,
        "fund_name": fund.name,
        **result,
        "disclaimer": "历史模拟不代表未来收益。定投回测仅展示过去数据推算，不构成投资建议。",
    }


# ---------------------------------------------------------------------------
# Investment Guru Commentary
# ---------------------------------------------------------------------------

@app.get("/api/funds/{code}/commentary")
def fund_commentary(code: str, db: Session = Depends(get_db)):
    """Generate investment guru commentary based on fund metrics."""
    fund = db.query(Fund).filter(Fund.code == code).first()
    if not fund:
        raise HTTPException(status_code=404, detail=f"Fund '{code}' not found")

    ensure_nav_data(code)

    nav_records = (
        db.query(FundNav)
        .filter(FundNav.fund_id == fund.id)
        .order_by(FundNav.nav_date.asc())
        .all()
    )

    nav_list = [
        {
            "nav_date": n.nav_date,
            "unit_nav": n.unit_nav,
            "cumulative_nav": n.cumulative_nav,
            "daily_return": n.daily_return,
        }
        for n in nav_records
    ]

    if not nav_list:
        raise HTTPException(status_code=404, detail="No NAV data available")

    metrics = compute_all_metrics(nav_list)
    pe_data = fund_pe_ratio(code)
    metrics["pe_ratio"] = pe_data

    holdings_count = db.query(Holding).filter(Holding.fund_id == fund.id).count()

    commentary = generate_commentary(
        fund_name=fund.name,
        fund_type=fund.fund_type,
        metrics=metrics,
        holdings_count=holdings_count,
    )

    return {
        "fund_code": code,
        "fund_name": fund.name,
        "fund_type": fund.fund_type,
        "commentary": commentary,
        "disclaimer": "内容仅供参考，不构成投资建议。投资有风险，过往业绩不预示未来表现。",
    }


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
