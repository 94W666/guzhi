"""Fund performance metrics from historical NAV data.

All functions operate on sequences of NAV data (dicts with keys:
``nav_date``, ``unit_nav``, ``cumulative_nav``, ``daily_return``)
sorted by date ascending.
"""

import math
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from typing import Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slice_by_period(nav_list: list[dict], period: str) -> list[dict]:
    """Return the tail of ``nav_list`` corresponding to a time period.

    ``period`` values: ``"1y"``, ``"3y"``, ``"5y"``, ``"ytd"``, ``"all"``.
    ``nav_date`` values may be ``date`` objects or ISO-format strings.
    """
    if not nav_list or period == "all":
        return nav_list

    today = date.today()
    delta_map = {"1y": 365, "3y": 1095, "5y": 1825}
    if period == "ytd":
        cutoff = date(today.year, 1, 1)
    elif period in delta_map:
        cutoff = today - timedelta(days=delta_map[period])
    else:
        return nav_list

    def _to_date(d):
        if isinstance(d, str):
            return date.fromisoformat(d)
        return d

    return [n for n in nav_list if _to_date(n["nav_date"]) >= cutoff]


def _period_cutoff_date(period: str) -> Optional[date]:
    """Return the cutoff date for a NAV query period, or None for 'all'."""
    if period == "all":
        return None
    today = date.today()
    if period == "ytd":
        return date(today.year, 1, 1)
    delta_map = {"1y": 365, "3y": 1095, "5y": 1825}
    if period in delta_map:
        return today - timedelta(days=delta_map[period])
    return None


def _get_rf_rate() -> float:
    """Return the default risk-free rate (China 10Y gov bond ~2.5%)."""
    return 0.025


# ---------------------------------------------------------------------------
# Max Drawdown
# ---------------------------------------------------------------------------

def max_drawdown(nav_list: list[dict], period: str = "all") -> dict:
    """Compute the maximum drawdown over a given period.

    Uses cumulative NAV (or unit NAV if cumulative unavailable).

    Returns::

        {
            "mdd": float (negative value, e.g. -0.183),
            "peak_date": str | None,
            "trough_date": str | None,
            "period": str,
        }
    """
    data = _slice_by_period(nav_list, period)
    if len(data) < 2:
        return {"mdd": 0.0, "peak_date": None, "trough_date": None, "period": period}

    peak = data[0]["cumulative_nav"] or data[0]["unit_nav"]
    peak_date = data[0]["nav_date"]
    mdd = 0.0
    trough_date = peak_date
    mdd_peak_date = peak_date

    for row in data[1:]:
        nav = row["cumulative_nav"] or row["unit_nav"]
        if nav > peak:
            peak = nav
            peak_date = row["nav_date"]
            continue

        dd = (nav - peak) / peak if peak > 0 else 0.0
        if dd < mdd:
            mdd = dd
            mdd_peak_date = peak_date
            trough_date = row["nav_date"]

    return {
        "mdd": round(mdd, 4),
        "peak_date": mdd_peak_date.isoformat() if mdd < 0 else None,
        "trough_date": trough_date.isoformat() if mdd < 0 else None,
        "period": period,
    }


# ---------------------------------------------------------------------------
# Annualized Return
# ---------------------------------------------------------------------------

def annualized_return(nav_list: list[dict], period: str = "all") -> Optional[float]:
    """Compute the annualized return over *period* (1y, 3y, 5y, ytd, all).

    ``CAGR = (end_nav / start_nav) ^ (365 / days) - 1``
    """
    data = _slice_by_period(nav_list, period)
    if len(data) < 2:
        return None

    start_nav = data[0]["cumulative_nav"] or data[0]["unit_nav"]
    end_nav = data[-1]["cumulative_nav"] or data[-1]["unit_nav"]

    if start_nav <= 0:
        return None

    days = (data[-1]["nav_date"] - data[0]["nav_date"]).days
    if days == 0:
        return 0.0

    return (end_nav / start_nav) ** (365.0 / days) - 1.0


def all_returns(nav_list: list[dict]) -> dict:
    """Return annualized returns for all standard periods."""
    periods = ["1y", "3y", "5y", "ytd"]
    result: dict = {}
    for p in periods:
        r = annualized_return(nav_list, p)
        result[p] = round(r, 4) if r is not None else None

    # Since inception
    r_all = annualized_return(nav_list, "all")
    result["since_inception"] = round(r_all, 4) if r_all is not None else None

    return result


# ---------------------------------------------------------------------------
# Volatility
# ---------------------------------------------------------------------------

def volatility(nav_list: list[dict], period: str = "1y") -> Optional[float]:
    """Annualized volatility (std of daily returns * sqrt(252))."""
    data = _slice_by_period(nav_list, period)
    returns = [n["daily_return"] for n in data if n.get("daily_return") is not None]

    if len(returns) < 2:
        return None

    n = len(returns)
    mean = sum(returns) / n
    variance = sum((r - mean) ** 2 for r in returns) / (n - 1)
    return math.sqrt(variance) * math.sqrt(252)


def all_volatilities(nav_list: list[dict]) -> dict:
    """Return annualized volatility for 1y, 3y, 5y."""
    result: dict = {}
    for p in ("1y", "3y", "5y"):
        v = volatility(nav_list, p)
        result[p] = round(v, 4) if v is not None else None
    return result


# ---------------------------------------------------------------------------
# Sharpe Ratio
# ---------------------------------------------------------------------------

def sharpe_ratio(nav_list: list[dict], period: str = "1y") -> Optional[float]:
    """Sharpe Ratio = (annualized_return - risk_free_rate) / volatility."""
    ann_ret = annualized_return(nav_list, period)
    vol = volatility(nav_list, period)

    if ann_ret is None or vol is None or vol == 0:
        return None

    return (ann_ret - _get_rf_rate()) / vol


def all_sharpes(nav_list: list[dict]) -> dict:
    """Return Sharpe ratios for 1y, 3y, 5y."""
    result: dict = {}
    for p in ("1y", "3y", "5y"):
        s = sharpe_ratio(nav_list, p)
        result[p] = round(s, 4) if s is not None else None
    return result


# ---------------------------------------------------------------------------
# Bonus metrics
# ---------------------------------------------------------------------------

def sortino_ratio(nav_list: list[dict], period: str = "1y") -> Optional[float]:
    """Sortino Ratio: uses downside deviation instead of total volatility."""
    data = _slice_by_period(nav_list, period)
    returns = [n["daily_return"] for n in data if n.get("daily_return") is not None]

    if len(returns) < 2:
        return None

    # Downside returns only (negative returns)
    downside = [r for r in returns if r < 0]
    if len(downside) < 2:
        return None

    n = len(downside)
    mean_down = sum(downside) / n
    downside_var = sum((r - mean_down) ** 2 for r in downside) / (n - 1)
    downside_dev = math.sqrt(downside_var) * math.sqrt(252)

    ann_ret = annualized_return(nav_list, period)
    if ann_ret is None or downside_dev == 0:
        return None

    return (ann_ret - _get_rf_rate()) / downside_dev


def calmar_ratio(nav_list: list[dict], period: str = "3y") -> Optional[float]:
    """Calmar Ratio = annualized_return / |max_drawdown|."""
    ann_ret = annualized_return(nav_list, period)
    mdd_result = max_drawdown(nav_list, period)

    if ann_ret is None or mdd_result["mdd"] == 0:
        return None

    return ann_ret / abs(mdd_result["mdd"])


def win_rate(nav_list: list[dict], period: str = "1y") -> Optional[float]:
    """Percentage of days with positive return."""
    data = _slice_by_period(nav_list, period)
    returns = [n["daily_return"] for n in data if n.get("daily_return") is not None]

    if not returns:
        return None

    positive = sum(1 for r in returns if r > 0)
    return positive / len(returns)


# ---------------------------------------------------------------------------
# Comprehensive summary
# ---------------------------------------------------------------------------

def compute_all_metrics(nav_list: list[dict]) -> dict:
    """Compute a complete metrics summary for a fund's NAV history."""
    return {
        "returns": all_returns(nav_list),
        "max_drawdown": {
            "1y": max_drawdown(nav_list, "1y"),
            "3y": max_drawdown(nav_list, "3y"),
            "5y": max_drawdown(nav_list, "5y"),
            "since_inception": max_drawdown(nav_list, "all"),
        },
        "volatility": all_volatilities(nav_list),
        "sharpe": all_sharpes(nav_list),
        "sortino": {
            "1y": round(sortino_ratio(nav_list, "1y"), 4) if sortino_ratio(nav_list, "1y") is not None else None,
            "3y": round(sortino_ratio(nav_list, "3y"), 4) if sortino_ratio(nav_list, "3y") is not None else None,
        },
        "calmar": {
            "1y": round(calmar_ratio(nav_list, "1y"), 4) if calmar_ratio(nav_list, "1y") is not None else None,
            "3y": round(calmar_ratio(nav_list, "3y"), 4) if calmar_ratio(nav_list, "3y") is not None else None,
        },
        "win_rate": {
            "1y": round(win_rate(nav_list, "1y"), 4) if win_rate(nav_list, "1y") is not None else None,
            "3y": round(win_rate(nav_list, "3y"), 4) if win_rate(nav_list, "3y") is not None else None,
        },
    }


# ---------------------------------------------------------------------------
# PE Ratio (fund-level)
# ---------------------------------------------------------------------------

# In-memory PE cache: {fund_code: (timestamp, result_dict)}
_pe_cache: dict[str, tuple[float, dict]] = {}
_PE_CACHE_TTL = 300  # 5 minutes


def fund_pe_ratio(fund_code: str) -> dict:
    """Compute fund-level P/E ratio as a weighted harmonic mean.

    Fetches current holdings from DB, then gets P/E (TTM) for each stock
    via the Eastmoney push2 API. Results are cached for 5 minutes.

    Returns::

        {
            "pe": float | None,
            "stock_pes": {stock_code: pe},
            "missing": [stock_codes without PE data],
        }
    """
    # Check cache
    now = time.time()
    if fund_code in _pe_cache:
        ts, cached = _pe_cache[fund_code]
        if now - ts < _PE_CACHE_TTL:
            return cached

    from database import SessionLocal
    from models import Fund, Holding

    db = SessionLocal()
    try:
        fund = db.query(Fund).filter(Fund.code == fund_code).first()
        if not fund:
            result = {"pe": None, "stock_pes": {}, "missing": []}
            _pe_cache[fund_code] = (now, result)
            return result

        holdings = db.query(Holding).filter(Holding.fund_id == fund.id).all()
    finally:
        db.close()

    if not holdings:
        result = {"pe": None, "stock_pes": {}, "missing": []}
        _pe_cache[fund_code] = (now, result)
        return result

    # Build stock list
    stocks = list({h.stock_code for h in holdings})
    weights = {h.stock_code: h.weight for h in holdings}

    # Fetch P/E data from Eastmoney (parallel, best-effort)
    try:
        stock_pes = _fetch_stock_pes(stocks)
    except Exception:
        stock_pes = {}

    # Compute weighted harmonic mean
    total_weight = sum(weights.values())
    if total_weight == 0:
        result = {"pe": None, "stock_pes": stock_pes, "missing": []}
        _pe_cache[fund_code] = (now, result)
        return result

    harmonic_sum = 0.0
    weight_used = 0.0
    missing = []

    for stock_code, weight in weights.items():
        pe = stock_pes.get(stock_code)
        if pe and pe > 0:
            norm_weight = weight / total_weight
            harmonic_sum += norm_weight / pe
            weight_used += norm_weight
        else:
            missing.append(stock_code)

    if harmonic_sum == 0 or weight_used < 0.5:
        result = {"pe": None, "stock_pes": stock_pes, "missing": missing}
        _pe_cache[fund_code] = (now, result)
        return result

    fund_pe = round(1.0 / harmonic_sum, 2)
    result = {"pe": fund_pe, "stock_pes": stock_pes, "missing": missing}
    _pe_cache[fund_code] = (now, result)
    return result


# ---------------------------------------------------------------------------
# PE-based Valuation Assessment (deprecated)
# ---------------------------------------------------------------------------

def valuation_assessment(fund_name: str, fund_type: str, pe: Optional[float],
                         tracking_index: str = "") -> dict:
    """[deprecated] Assess fund valuation based on portfolio PE ratio.

    Uses the weighted PE of underlying holdings (not NAV) — this is the
    correct valuation metric for both index and active funds.  NAV percentile
    is intentionally NOT used because active funds should always trend upward,
    making NAV-based "percentile" meaningless.

    Returns::

        {
            "pe": float | None,
            "assessment": "低估" | "合理" | "偏贵" | "高估" | "无数据",
            "color": "green" | "yellow" | "orange" | "red" | "gray",
            "pe_pct": float (0-100, position on PE scale),
            "explanation": str,
        }
    """
    result = {"pe": pe, "assessment": "无数据", "color": "gray", "pe_pct": 50, "explanation": ""}

    if pe is None or pe <= 0:
        result["explanation"] = "暂无法获取持仓PE数据。基金持仓的实时市盈率需要美股/A股行情源支持，当前数据源暂不可用。"
        return result

    # PE scale: map PE to 0-100 gauge position (0=PE 5, 100=PE 45)
    pe_pct = max(0, min(100, (pe - 5) / 40 * 100))
    result["pe_pct"] = round(pe_pct, 1)

    # Assessment based on PE range
    if pe < 12:
        assessment = "低估"
        color = "green"
        explanation = f"持仓加权PE仅 {pe:.1f}，处于明显低估区间。多数行业PE低于12意味着市场对其盈利前景悲观，但这也可能意味着较高的安全边际。"
    elif pe < 18:
        assessment = "偏低"
        color = "green"
        explanation = f"持仓加权PE {pe:.1f}，估值偏低。对于价值投资者而言，这个区间的风险回报比通常较好。"
    elif pe < 25:
        assessment = "合理"
        color = "yellow"
        explanation = f"持仓加权PE {pe:.1f}，处于合理区间。若为宽基指数，此PE接近长期均值；若为成长行业，则可能仍属合理。"
    elif pe < 35:
        assessment = "偏贵"
        color = "orange"
        explanation = f"持仓加权PE {pe:.1f}，估值偏贵。市场给予了这些公司较高的成长预期。如果未来盈利增长不及预期，PE可能面临下调。"
    else:
        assessment = "高估"
        color = "red"
        explanation = f"持仓加权PE {pe:.1f}，估值较高。虽然高PE可能反映高增长预期，但安全边际很小。历史上的高PE区间往往伴随着更大的回撤风险。"

    # Add context based on fund type
    is_index = any(kw in (fund_name or "") for kw in ["指数", "ETF", "标普", "500", "沪深", "中证"])
    is_overseas = "QDII" in (fund_type or "")

    if is_index and is_overseas:
        explanation += " 作为QDII指数基金，持仓PE直接反映海外市场的估值水平。"
        if "标普" in (fund_name or ""):
            explanation += "标普500长期PE中枢约在15-18，当前水平可与该区间对比判断贵贱。"
    elif is_index:
        explanation += " 作为指数基金，PE反映了所跟踪市场的整体估值温度。"
    else:
        explanation += " 注：此为主动管理基金，PE仅反映当前持仓的估值，不代表基金经理未来不会调仓。PE高可能因为该基金经理偏好高成长标的。"

    result["assessment"] = assessment
    result["color"] = color
    result["explanation"] = explanation
    result["is_index"] = is_index

    return result


# ---------------------------------------------------------------------------
# DCA (Dollar-Cost Averaging) Backtest
# ---------------------------------------------------------------------------

def dca_backtest(nav_list: list[dict], monthly_amount: float = 1000.0, years: int = 3) -> dict:
    """Simulate monthly dollar-cost averaging over the last *years*.

    Invests *monthly_amount* on the first trading day of each month.
    Compares final value against lump-sum investment at the start.

    Returns::

        {
            "monthly_amount": float,
            "years": int,
            "total_invested": float,
            "final_value": float,
            "total_return_pct": float,
            "annualized_return_pct": float,
            "avg_cost_per_share": float,
            "current_nav": float,
            "lump_sum": { "invested", "final_value", "return_pct", "annualized_pct" },
            "monthly": [{date, nav, shares_bought, total_shares, cost_basis, value}],
        }
    """
    today = date.today()
    cutoff = today - timedelta(days=years * 365)
    period_data = [n for n in nav_list if n["nav_date"] >= cutoff]
    if len(period_data) < 12:
        return None

    # Group by year-month, picking the first trading day of each month
    month_groups: dict[str, dict] = {}
    for n in period_data:
        key = n["nav_date"].strftime("%Y-%m")
        if key not in month_groups or n["nav_date"] < month_groups[key]["nav_date"]:
            month_groups[key] = {"nav_date": n["nav_date"], "unit_nav": n["unit_nav"]}

    monthly_points = sorted(month_groups.values(), key=lambda x: x["nav_date"])

    # Lump-sum: invest everything at the first point
    first_nav = monthly_points[0]["unit_nav"]
    total_invested = monthly_amount * len(monthly_points)
    lump_shares = total_invested / first_nav if first_nav > 0 else 0
    current_nav = period_data[-1]["unit_nav"]
    lump_value = lump_shares * current_nav

    # DCA: invest monthly_amount on each month's first day
    total_shares = 0.0
    cumulative_invested = 0.0
    monthly = []

    for m in monthly_points:
        nav = m["unit_nav"]
        if nav > 0:
            shares = monthly_amount / nav
            total_shares += shares
        else:
            shares = 0
        cumulative_invested += monthly_amount

        # avg_cost = total_invested_so_far / total_shares_so_far
        current_cost = cumulative_invested / total_shares if total_shares > 0 else 0

        monthly.append({
            "date": m["nav_date"].isoformat(),
            "nav": round(nav, 4),
            "shares_bought": round(shares, 4),
            "total_shares": round(total_shares, 4),
            "cumulative_invested": round(cumulative_invested, 2),
            "cost_basis": round(current_cost, 4),
            "value": round(total_shares * nav, 2),
        })

    dca_value = total_shares * current_nav
    dca_return = (dca_value - total_invested) / total_invested if total_invested > 0 else 0
    dca_ann = (1 + dca_return) ** (1.0 / years) - 1 if years > 0 else 0

    lump_return = (lump_value - total_invested) / total_invested if total_invested > 0 else 0
    lump_ann = (1 + lump_return) ** (1.0 / years) - 1 if years > 0 else 0

    return {
        "monthly_amount": monthly_amount,
        "years": years,
        "total_months": len(monthly_points),
        "start_date": monthly_points[0]["nav_date"].isoformat(),
        "end_date": period_data[-1]["nav_date"].isoformat(),
        "total_invested": round(total_invested, 2),
        "final_value": round(dca_value, 2),
        "total_return_pct": round(dca_return * 100, 2),
        "annualized_return_pct": round(dca_ann * 100, 2),
        "avg_cost_per_share": round(total_invested / total_shares, 4) if total_shares > 0 else 0,
        "current_nav": round(current_nav, 4),
        "total_shares": round(total_shares, 4),
        "lump_sum": {
            "invested": round(total_invested, 2),
            "final_value": round(lump_value, 2),
            "return_pct": round(lump_return * 100, 2),
            "annualized_pct": round(lump_ann * 100, 2),
        },
        "monthly": monthly,
    }


def _fetch_stock_pes(stocks: list[str]) -> dict[str, Optional[float]]:
    """Fetch P/E TTM for each stock via Eastmoney push2 API — parallel.

    Uses ThreadPoolExecutor to fetch all stocks concurrently, reducing
    total time from sum(all) to max(single).

    Returns ``{stock_code: pe_value|None}``.
    """
    import httpx

    if not stocks:
        return {}

    def _market_prefix(code: str) -> str:
        c = code.strip()
        if c[0].isalpha():
            return "106"  # NASDAQ default for US tickers
        if c.startswith(("60", "68")):
            return "1"  # Shanghai
        if c.startswith(("00", "30")):
            return "0"  # Shenzhen
        return "106"

    SINGLE_URL = "https://push2.eastmoney.com/api/qt/stock/get"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "https://quote.eastmoney.com/",
    }

    # Deduplicate
    unique = list(dict.fromkeys(stocks))  # preserves order, removes dups

    def _fetch_one(s: str) -> tuple[str, Optional[float]]:
        market = _market_prefix(s)
        params = {
            "secid": f"{market}.{s}",
            "fields": "f57,f115",
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
        }
        try:
            with httpx.Client(timeout=10, headers=headers) as client:
                resp = client.get(SINGLE_URL, params=params)
                resp.raise_for_status()
                item = resp.json().get("data")
        except Exception:
            return (s, None)

        if not item or not isinstance(item, dict):
            return (s, None)

        pe_val = item.get("f115")
        if pe_val is not None and pe_val != "-" and pe_val != "":
            try:
                pe = float(pe_val)
                if pe > 0:
                    return (s, pe)
            except (ValueError, TypeError):
                pass
        return (s, None)

    result: dict[str, Optional[float]] = {}
    # Parallel fetch — one thread per stock, timeout per stock
    with ThreadPoolExecutor(max_workers=min(len(unique), 10)) as pool:
        futures = {pool.submit(_fetch_one, s): s for s in unique}
        for future in as_completed(futures):
            try:
                code, pe_val = future.result(timeout=12)
                if pe_val is not None:
                    result[code] = pe_val
            except Exception:
                pass

    return result
