"""Fetch historical NAV data from Eastmoney pingzhongdata API.

Data source: ``https://fund.eastmoney.com/pingzhongdata/{fund_code}.js``
Parses ``Data_netWorthTrend`` (unit NAV) and ``Data_ACWorthTrend``
(cumulative NAV) from the JavaScript response.
"""

import re
import json
import sys
import os
from datetime import date, datetime, timedelta
from typing import Optional

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import FUND_DETAIL_URL


# ---------------------------------------------------------------------------
# API fetching
# ---------------------------------------------------------------------------

def fetch_nav_history(fund_code: str) -> Optional[dict]:
    """Fetch complete NAV history for a fund.

    Returns a dict with two lists:
      - ``unit_nav``: ``[{date, nav}, ...]``  from Data_netWorthTrend
      - ``cumulative_nav``: ``[{date, nav}, ...]``  from Data_ACWorthTrend

    Returns ``None`` if the request or parsing fails.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": f"https://fund.eastmoney.com/{fund_code}.html",
    }

    url = FUND_DETAIL_URL.format(fund_code=fund_code)

    with httpx.Client(timeout=30, headers=headers) as client:
        resp = client.get(url)
        resp.raise_for_status()

    text = resp.text

    # --- Parse Data_netWorthTrend: [{x: timestamp_ms, y: unit_nav}, ...] ---
    unit_nav: list[dict] = []
    m = re.search(r"var Data_netWorthTrend\s*=\s*(\[.*?\]);", text, re.DOTALL)
    if m:
        try:
            raw = json.loads(m.group(1))
            for item in raw:
                ts = item.get("x", 0)
                nav = item.get("y", 0)
                if ts:
                    unit_nav.append({
                        "date": date.fromtimestamp(ts / 1000),
                        "nav": nav,
                    })
        except (json.JSONDecodeError, KeyError):
            pass

    # --- Parse Data_ACWorthTrend: [[timestamp_ms, cumulative_nav], ...] ---
    cumulative_nav: list[dict] = []
    m = re.search(r"var Data_ACWorthTrend\s*=\s*(\[.*?\]);", text, re.DOTALL)
    if m:
        try:
            raw = json.loads(m.group(1))
            for item in raw:
                ts = item[0]
                nav = item[1]
                if ts:
                    cumulative_nav.append({
                        "date": date.fromtimestamp(ts / 1000),
                        "nav": nav,
                    })
        except (json.JSONDecodeError, IndexError):
            pass

    if not unit_nav and not cumulative_nav:
        return None

    return {
        "unit_nav": unit_nav,
        "cumulative_nav": cumulative_nav,
    }


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def save_nav_to_db(fund_id: int, nav_data: dict) -> int:
    """Persist NAV history to the database.

    Merges unit and cumulative NAV by date, computes daily returns,
    and upserts by ``(fund_id, nav_date)``.

    Returns the number of records saved.
    """
    from database import SessionLocal, init_db
    from models import FundNav

    init_db()
    db = SessionLocal()

    # Merge unit + cumulative NAV by date
    unit_map: dict[date, float] = {
        item["date"]: item["nav"] for item in nav_data.get("unit_nav", [])
    }
    cum_map: dict[date, float] = {
        item["date"]: item["nav"] for item in nav_data.get("cumulative_nav", [])
    }
    all_dates = sorted(set(unit_map.keys()) | set(cum_map.keys()))

    if not all_dates:
        db.close()
        return 0

    # Compute daily returns from unit NAV (cumulative NAV not suitable)
    records: list[dict] = []
    for i, d in enumerate(all_dates):
        unit = unit_map.get(d, 0.0)
        cum = cum_map.get(d, 0.0)

        daily_ret = 0.0
        if i > 0:
            prev_unit = unit_map.get(all_dates[i - 1], 0.0)
            if prev_unit and prev_unit > 0:
                daily_ret = (unit / prev_unit) - 1.0

        records.append({
            "nav_date": d,
            "unit_nav": unit,
            "cumulative_nav": cum,
            "daily_return": daily_ret,
        })

    try:
        saved = 0
        for rec in records:
            existing = db.query(FundNav).filter(
                FundNav.fund_id == fund_id,
                FundNav.nav_date == rec["nav_date"],
            ).first()

            if existing:
                existing.unit_nav = rec["unit_nav"]
                existing.cumulative_nav = rec["cumulative_nav"]
                existing.daily_return = rec["daily_return"]
            else:
                db.add(FundNav(
                    fund_id=fund_id,
                    nav_date=rec["nav_date"],
                    unit_nav=rec["unit_nav"],
                    cumulative_nav=rec["cumulative_nav"],
                    daily_return=rec["daily_return"],
                ))
            saved += 1

        db.commit()
        return saved
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# One-stop helper for API layer
# ---------------------------------------------------------------------------

def ensure_nav_data(fund_code: str) -> int:
    """Ensure NAV data exists in DB for a given fund code.

    Checks if the fund exists and if NAV data is already present.
    Fetches and saves fresh data if needed.

    Returns the number of NAV records available.
    """
    from database import SessionLocal
    from models import Fund, FundNav

    db = SessionLocal()
    try:
        fund = db.query(Fund).filter(Fund.code == fund_code).first()
        if not fund:
            return 0

        # Check if we already have data
        count = db.query(FundNav).filter(FundNav.fund_id == fund.id).count()
        if count > 0:
            return count

        # Need to fetch
        fund_id = fund.id
    finally:
        db.close()

    nav_data = fetch_nav_history(fund_code)
    if not nav_data:
        return 0

    return save_nav_to_db(fund_id, nav_data)


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fetch NAV history for a fund")
    parser.add_argument("fund_code", help="Fund code (e.g. 005698)")
    args = parser.parse_args()

    print(f"Fetching NAV history for {args.fund_code}...")
    nav_data = fetch_nav_history(args.fund_code)

    if not nav_data:
        print("  Failed to fetch NAV data")
        sys.exit(1)

    unit_count = len(nav_data.get("unit_nav", []))
    cum_count = len(nav_data.get("cumulative_nav", []))
    print(f"  Parsed {unit_count} unit NAV records, {cum_count} cumulative NAV records")

    if unit_count > 0:
        first = nav_data["unit_nav"][0]
        last = nav_data["unit_nav"][-1]
        print(f"  Unit NAV range: {first['date']} ({first['nav']}) ~ {last['date']} ({last['nav']})")

    # Save to DB
    from database import SessionLocal
    from models import Fund

    db = SessionLocal()
    try:
        fund = db.query(Fund).filter(Fund.code == args.fund_code).first()
        if not fund:
            print(f"  Fund {args.fund_code} not in database — saving NAV data requires fund to exist first")
            sys.exit(1)
        fund_id = fund.id
    finally:
        db.close()

    saved = save_nav_to_db(fund_id, nav_data)
    print(f"  Saved {saved} NAV records to database")
