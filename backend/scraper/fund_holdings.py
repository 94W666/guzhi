"""Scrape fund top-10 holdings from Eastmoney Fund Archives API.

Data source: https://fundf10.eastmoney.com/FundArchivesDatas.aspx
The API returns a JavaScript variable assignment containing an HTML table of
the fund's top holdings (stock code, name, weight).
"""

import re
import sys
import os
import random
from datetime import date, timedelta
from typing import Optional

import httpx
from bs4 import BeautifulSoup

# Allow running as standalone script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import FUND_HOLDINGS_URL


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------

def _parse_js_response(text: str) -> Optional[dict]:
    """Parse a JavaScript variable-assignment response into a dict.

    Expected input: ``var apidata={ content:"<table>...</table>", count:10, … }``
    Keys are unquoted JavaScript identifiers; *content* is a JS-escaped string.
    """
    text = text.strip()
    result: dict = {}

    # --- content (may contain escaped double-quotes) ---
    content_match = re.search(r'content:"((?:[^"\\]|\\.)*)"', text)
    if content_match:
        html = content_match.group(1)
        html = _unescape_js_string(html)
        result["content"] = html

    # --- integer fields ---
    for field in ("count", "records", "pages", "curpage"):
        m = re.search(rf"\b{field}:(\d+)", text)
        if m:
            result[field] = int(m.group(1))

    # --- string fields ---
    for field in ("year", "month"):
        m = re.search(rf'\b{field}:"(\d*)"', text)
        if m:
            result[field] = m.group(1)

    return result if result else None


def _unescape_js_string(s: str) -> str:
    """Minimal JS-string unescaping: backslash-escaped characters."""
    result: list[str] = []
    i = 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            result.append(s[i + 1])
            i += 2
        else:
            result.append(s[i])
            i += 1
    return "".join(result)


# ---------------------------------------------------------------------------
# HTML table parsing
# ---------------------------------------------------------------------------

def _parse_html_table(html_content: str) -> list[dict]:
    """Extract holdings from the API-returned HTML table.

    Returns a list of dicts with keys ``stock_code``, ``stock_name``, ``weight``.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    table = soup.find("table")
    if not table:
        return []

    holdings: list[dict] = []
    tbody = table.find("tbody")
    rows = (tbody if tbody else table).find_all("tr")

    for row in rows:
        cells = row.find_all("td")
        # Table columns: 序号(0), 股票代码(1), 股票名称(2), 最新价(3),
        # 涨跌额(4), 相关资讯(5), 占净值比例(6), 持股数(7), 持仓市值(8)
        if len(cells) < 7:               # skip header / spacer rows
            continue

        stock_code = cells[1].get_text(strip=True)
        stock_name = cells[2].get_text(strip=True)
        weight_str = cells[6].get_text(strip=True).replace("%", "").strip()

        if not stock_code:
            continue

        try:
            weight = float(weight_str)
        except ValueError:
            weight = 0.0

        holdings.append({
            "stock_code": stock_code,
            "stock_name": stock_name,
            "weight": weight,
        })

    return holdings


# ---------------------------------------------------------------------------
# Date & classification helpers
# ---------------------------------------------------------------------------

def _extract_report_date(api_data: dict, html_content: str = "") -> date:
    """Derive the quarterly report date.

    Tries *year* / *month* fields first, then falls back to extracting a
    ``YYYY-MM-DD`` date from the HTML (the Eastmoney API embeds the cutoff
    date in a label like ``<font>2026-03-31</font>``).
    """
    year_str = api_data.get("year")
    month_str = api_data.get("month")
    if year_str and month_str:
        year = int(year_str)
        month = int(month_str)
        if month == 12:
            next_month = date(year + 1, 1, 1)
        else:
            next_month = date(year, month + 1, 1)
        return next_month - timedelta(days=1)

    # Fallback: scan the HTML for a date string
    if html_content:
        m = re.search(r"(\d{4})-(\d{2})-(\d{2})", html_content)
        if m:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    return date.today()


def _classify_stock(stock_code: str) -> str:
    """Classify a stock by its code pattern.

    - **US**   – ticker starts with a letter (e.g. AAPL, MSFT)
    - **HK**   – code starts with a digit (e.g. 00700)
    - **OTHER** – everything else
    """
    if not stock_code:
        return "OTHER"
    first = stock_code[0]
    if first.isalpha():
        return "US"
    if first.isdigit():
        return "HK"
    return "OTHER"


# ---------------------------------------------------------------------------
# Main public API
# ---------------------------------------------------------------------------

def fetch_holdings(fund_code: str) -> Optional[tuple[list[dict], date]]:
    """Fetch top-10 holdings for a single fund.

    Returns ``(holdings, report_date)`` or ``None`` if the fund has no
    holdings data (common for bond / money-market funds).
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": f"https://fundf10.eastmoney.com/jjjc_{fund_code}.html",
    }

    params = {
        "type": "jjcc",
        "code": fund_code,
        "topline": "10",
        "year": "",
        "month": "",
        "rt": str(random.random()),
    }

    with httpx.Client(timeout=30, headers=headers) as client:
        resp = client.get(FUND_HOLDINGS_URL, params=params)
        resp.raise_for_status()

    api_data = _parse_js_response(resp.text)
    if not api_data:
        print(f"  Failed to parse JS response for fund {fund_code}")
        return None

    content = api_data.get("content", "")
    if not content:
        print(f"  No holdings data in response for fund {fund_code}")
        return None

    holdings = _parse_html_table(content)
    if not holdings:
        print(f"  No holdings parsed from table for fund {fund_code}")
        return None

    report_date = _extract_report_date(api_data, content)
    return holdings, report_date


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def save_holdings_to_db(fund_id: int, holdings: list[dict], report_date: date) -> int:
    """Persist holdings to the database (upsert by fund_id + stock_code + report_date).

    Returns the number of records saved.
    """
    from database import SessionLocal, init_db
    from models import Holding

    init_db()
    db = SessionLocal()

    try:
        saved = 0
        for h in holdings:
            existing = db.query(Holding).filter(
                Holding.fund_id == fund_id,
                Holding.stock_code == h["stock_code"],
                Holding.report_date == report_date,
            ).first()

            if existing:
                existing.stock_name = h["stock_name"]
                existing.weight = h["weight"]
            else:
                holding = Holding(
                    fund_id=fund_id,
                    stock_code=h["stock_code"],
                    stock_name=h["stock_name"],
                    weight=h["weight"],
                    report_date=report_date,
                )
                db.add(holding)
            saved += 1

        db.commit()
        return saved
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------

def batch_fetch_all() -> dict:
    """Iterate over every fund in the database and fetch its holdings.

    Returns a summary dict::

        {
            "total": int,
            "success": int,
            "failed": int,
            "no_holdings": int,
            "details": [ … ],
        }
    """
    from database import SessionLocal
    from models import Fund

    db = SessionLocal()
    try:
        funds = db.query(Fund).all()
    finally:
        db.close()

    results = {
        "total": len(funds),
        "success": 0,
        "failed": 0,
        "no_holdings": 0,
        "details": [],
    }

    for fund in funds:
        print(f"Fetching holdings for {fund.code} {fund.name}...")
        try:
            outcome = fetch_holdings(fund.code)
            if outcome is None:
                results["no_holdings"] += 1
                results["details"].append({
                    "code": fund.code,
                    "name": fund.name,
                    "status": "no_holdings",
                })
                continue

            holdings, report_date = outcome
            saved = save_holdings_to_db(fund.id, holdings, report_date)
            results["success"] += 1
            results["details"].append({
                "code": fund.code,
                "name": fund.name,
                "status": "success",
                "holdings_count": saved,
                "report_date": report_date.isoformat(),
            })
            print(f"  Saved {saved} holdings (report date: {report_date})")
        except Exception as e:
            results["failed"] += 1
            results["details"].append({
                "code": fund.code,
                "name": fund.name,
                "status": "failed",
                "error": str(e),
            })
            print(f"  Failed: {e}")

    return results
