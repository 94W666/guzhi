"""Scrape fund list from Eastmoney public API.

Data source: https://fund.eastmoney.com/data/rankhandler.aspx
The API returns a JSONP-like response containing fund rankings with codes, names, NAVs, etc.
"""

import json
import re
import sys
import os
from datetime import date, timedelta
from typing import Optional

import httpx

# Allow running as standalone script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import FUND_LIST_URL


def _parse_jsonp(text: str) -> Optional[dict]:
    """Extract JSON object from JSONP response like 'var rankData = {...};'

    Eastmoney uses unquoted JavaScript keys (not valid JSON), so we fix them
    before parsing.
    """
    text = text.strip()
    if text.startswith("var rankData = "):
        text = text[len("var rankData = "):]
    if text.endswith(";"):
        text = text[:-1]
    # Add double quotes around unquoted JavaScript object keys
    text = re.sub(r'(?<=[{,])\s*(\w+)\s*:', r'"\1":', text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def fetch_fund_list(fund_type: str = "qdii") -> list[dict]:
    """Fetch fund list from Eastmoney by type.

    Args:
        fund_type: Fund type filter — 'qdii', 'all', 'gp' (股票), 'hh' (混合), 'zq' (债券), etc.

    Returns a list of dicts with keys: code, name, fund_type, nav, cumulative_nav,
    daily_change, day_1, week_1, month_1, month_3, month_6, year_1, year_2, year_3,
    year_this, created_at, scale, tracking_index.
    """
    params = {
        "op": "ph",
        "dt": "kf",
        "ft": fund_type,
        "rs": "",
        "gs": "0",
        "sc": "zzf",
        "st": "desc",
        "sd": (date.today() - timedelta(days=730)).isoformat(),
        "ed": date.today().isoformat(),
        "qdii": "",
        "tabSubtype": ",,,,,",
        "pi": "1",
        "pn": "10000",
        "dx": "1",
        "v": "0.0",
    }

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "https://fund.eastmoney.com/data/fundranking.html",
    }

    with httpx.Client(timeout=30, headers=headers) as client:
        resp = client.get(FUND_LIST_URL, params=params)
        resp.raise_for_status()

    data = _parse_jsonp(resp.text)
    if not data:
        print("Failed to parse API response")
        return []

    funds = []
    raw_datas = data.get("datas", [])
    for entry in raw_datas:
        # Each entry is a comma-separated string:
        # 0:code, 1:name, 2:sp, 3:date, 4:jz, 5:ljjz, 6:daily, 7:week1,
        # 8:month1, 9:month3, 10:month6, 11:year1, 12:year2, 13:year3,
        # 14:yearThis, 15:sinceInception, 16:created, 17:flag, 18:scale, ...
        parts = entry.split(",")
        if len(parts) < 18:
            continue

        try:
            fund_info = {
                "code": parts[0].strip(),
                "name": parts[1].strip(),
                "fund_type": "OTHER" if fund_type == "all" else fund_type.upper(),
                "nav": float(parts[4]) if parts[4] else 0.0,
                "cumulative_nav": float(parts[5]) if parts[5] else 0.0,
                "daily_change": float(parts[6]) if parts[6] else 0.0,
                "week_1": float(parts[7]) if parts[7] else 0.0,
                "month_1": float(parts[8]) if parts[8] else 0.0,
                "month_3": float(parts[9]) if parts[9] else 0.0,
                "month_6": float(parts[10]) if parts[10] else 0.0,
                "year_1": float(parts[11]) if parts[11] else 0.0,
                "year_2": float(parts[12]) if parts[12] else 0.0,
                "year_3": float(parts[13]) if parts[13] else 0.0,
                "year_this": float(parts[14]) if parts[14] else 0.0,
                "created_at": parts[16].strip() if len(parts) > 16 else "",
                "scale": float(parts[18]) if len(parts) > 18 and parts[18] else 0.0,
                "tracking_index": "",
            }
            funds.append(fund_info)
        except (ValueError, IndexError) as e:
            print(f"Skipping malformed entry: {parts[:2]}, error: {e}")
            continue

    return funds


def filter_us_qdii(funds: list[dict]) -> list[dict]:
    """Filter QDII funds that primarily invest in US markets.

    Uses keyword matching on fund names. Common patterns:
    - Names containing: 美国, 纳斯达克, 标普, 道琼斯, 美股, 美元, US, S&P
    """
    us_keywords = [
        "美国", "纳斯达克", "标普", "道琼斯", "美股",
        "美元", "US", "S&P", "SP", "DJ", "nasdaq",
    ]

    us_funds = []
    for fund in funds:
        name = fund["name"]
        if any(kw.lower() in name.lower() for kw in us_keywords):
            fund_copy = fund.copy()
            fund_copy["tracking_index"] = _guess_tracking_index(name)
            us_funds.append(fund_copy)

    return us_funds


def _guess_tracking_index(name: str) -> str:
    """Guess the tracking index based on fund name keywords."""
    name_lower = name.lower()
    if "纳斯达克100" in name or "nasdaq100" in name_lower or "nasdaq 100" in name_lower:
        return "NASDAQ-100"
    if "纳斯达克" in name or "nasdaq" in name_lower:
        return "NASDAQ"
    if "标普500" in name or "s&p500" in name_lower or "s&p 500" in name_lower or "sp500" in name_lower:
        return "S&P 500"
    if "标普" in name or "s&p" in name_lower:
        return "S&P"
    if "道琼斯" in name or "dj" in name_lower:
        return "Dow Jones"
    if "美元" in name or "us" in name_lower:
        return "US Market"
    return "US Market"


def save_to_db(funds: list[dict]):
    """Save fund list to SQLite database. Upserts by fund code."""
    from database import SessionLocal, init_db
    from models import Fund

    init_db()
    db = SessionLocal()

    try:
        for f in funds:
            existing = db.query(Fund).filter(Fund.code == f["code"]).first()
            if existing:
                existing.name = f["name"]
                existing.scale = f.get("scale", 0.0)
                existing.tracking_index = f.get("tracking_index", "")
            else:
                fund = Fund(
                    code=f["code"],
                    name=f["name"],
                    fund_type=f.get("fund_type", "OTHER"),
                    tracking_index=f.get("tracking_index", ""),
                    scale=f.get("scale", 0.0),
                )
                db.add(fund)
        db.commit()
        print(f"Saved {len(funds)} funds to database")
    except Exception as e:
        db.rollback()
        print(f"Database error: {e}")
        raise
    finally:
        db.close()
