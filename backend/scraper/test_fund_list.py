"""Standalone test script for the QDII fund list scraper.

Usage: python scraper/test_fund_list.py
"""

import sys
import os

# Ensure the backend directory is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.fund_list import fetch_qdii_fund_list, filter_us_qdii, save_to_db


def main():
    print("=" * 60)
    print("QDII Fund List Scraper Test")
    print("=" * 60)

    # 1. Fetch all QDII funds
    print("\n[1] Fetching QDII fund list from Eastmoney...")
    all_funds = fetch_qdii_fund_list()

    if not all_funds:
        print("ERROR: No funds fetched. Check network connection or API availability.")
        return

    print(f"  Total QDII funds found: {len(all_funds)}")

    # 2. Filter US-market QDII funds
    print("\n[2] Filtering US-market QDII funds...")
    us_funds = filter_us_qdii(all_funds)
    print(f"  US-market QDII funds found: {len(us_funds)}")

    # 3. Print US QDII fund list
    print("\n[3] US QDII Fund List:")
    print(f"  {'Code':<8} {'Name':<35} {'Index':<20} {'Scale(亿)':>10}")
    print(f"  {'-'*8} {'-'*35} {'-'*20} {'-'*10}")
    for f in sorted(us_funds, key=lambda x: x["code"])[:50]:  # limit to 50 for readability
        print(f"  {f['code']:<8} {f['name']:<35} {f['tracking_index']:<20} {f.get('scale', 0):>10.2f}")

    if len(us_funds) > 50:
        print(f"  ... and {len(us_funds) - 50} more funds")

    # 4. Save to database
    print("\n[4] Saving US QDII funds to database...")
    save_to_db(us_funds)

    # 5. Verify database
    print("\n[5] Verifying database...")
    from database import SessionLocal
    from models import Fund

    db = SessionLocal()
    try:
        count = db.query(Fund).count()
        print(f"  Total funds in database: {count}")
        us_qdii = db.query(Fund).filter(Fund.fund_type == "QDII").all()
        us_qdii_us = [f for f in us_qdii if any(
            kw in (f.tracking_index or "") for kw in ["NASDAQ", "S&P", "Dow", "US"]
        )]
        print(f"  US-market funds in database: {len(us_qdii_us)}")
    finally:
        db.close()

    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
