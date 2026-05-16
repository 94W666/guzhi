"""Standalone test script for the fund holdings scraper.

Usage: python scraper/test_fund_holdings.py
"""

import sys
import os

# Ensure the backend directory is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.fund_holdings import (
    fetch_holdings,
    save_holdings_to_db,
    batch_fetch_all,
)


def test_sample_fund():
    """Test with 1-2 sample funds — human review of printed holdings."""
    print("=" * 60)
    print("Fund Holdings Scraper — Sample Fund Test")
    print("=" * 60)

    # Sample funds for testing
    test_codes = ["005698", "017642"]

    for code in test_codes:
        print(f"\n[Test] Fetching holdings for fund {code} …")
        result = fetch_holdings(code)

        if result is None:
            print(f"  WARNING: No holdings data returned for {code} (may be bond fund)")
            continue

        holdings, report_date = result
        print(f"  Report date: {report_date}")
        print(f"  Holdings count: {len(holdings)}")
        print()
        print(f"  {'Stock Code':<15} {'Stock Name':<35} {'Weight(%)':>10}")
        print(f"  {'-' * 15} {'-' * 35} {'-' * 10}")

        for h in holdings:
            print(f"  {h['stock_code']:<15} {h['stock_name']:<35} {h['weight']:>10.2f}")

        # Save to database (only if fund exists)
        from database import SessionLocal
        from models import Fund

        db = SessionLocal()
        try:
            fund = db.query(Fund).filter(Fund.code == code).first()
            if fund is None:
                print(f"\n  Fund {code} not in database — run test_fund_list.py first. Skipping DB save.")
                continue

            count = save_holdings_to_db(fund.id, holdings, report_date)
            print(f"\n  Saved {count} holdings to DB (fund_id={fund.id})")

            # Verify
            from models import Holding
            verify = (
                db.query(Holding)
                .filter(
                    Holding.fund_id == fund.id,
                    Holding.report_date == report_date,
                )
                .count()
            )
            print(f"  Verified: {verify} holdings in database")
        finally:
            db.close()


def test_upsert():
    """Re-run save to confirm upsert doesn't duplicate rows."""
    print("\n" + "=" * 60)
    print("Upsert Test — re-running save for fund 005698")
    print("=" * 60)

    result = fetch_holdings("005698")
    if result is None:
        print("  No holdings — skipping upsert test")
        return

    from database import SessionLocal
    from models import Fund, Holding

    holdings, report_date = result

    db = SessionLocal()
    try:
        fund = db.query(Fund).filter(Fund.code == "005698").first()
        if fund is None:
            print("  Fund not in DB — skipping")
            return

        # Count before
        before = db.query(Holding).filter(
            Holding.fund_id == fund.id,
            Holding.report_date == report_date,
        ).count()
        print(f"  Holdings for {report_date} before 2nd save: {before}")

        save_holdings_to_db(fund.id, holdings, report_date)

        after = db.query(Holding).filter(
            Holding.fund_id == fund.id,
            Holding.report_date == report_date,
        ).count()
        print(f"  Holdings for {report_date} after  2nd save: {after}")

        if before == after:
            print("  PASS: Upsert did not create duplicates")
        else:
            print(f"  FAIL: count changed from {before} to {after}")
    finally:
        db.close()


def test_batch_fetch():
    """Batch fetch holdings for every fund in the database."""
    print("\n" + "=" * 60)
    print("Fund Holdings Scraper — Batch Fetch")
    print("=" * 60)

    results = batch_fetch_all()

    print(f"\nSummary:")
    print(f"  Total funds:  {results['total']}")
    print(f"  Success:           {results['success']}")
    print(f"  Failed:            {results['failed']}")
    print(f"  No holdings:       {results['no_holdings']}")

    if results["failed"]:
        print(f"\n  Failed funds:")
        for d in results["details"]:
            if d["status"] == "failed":
                print(f"    {d['code']} {d['name']}: {d['error']}")

    # Quick DB count
    from database import SessionLocal
    from models import Holding

    db = SessionLocal()
    try:
        total = db.query(Holding).count()
        print(f"\n  Total holdings in database: {total}")
    finally:
        db.close()


def main():
    test_sample_fund()
    test_upsert()

    print("\n" + "=" * 60)
    resp = input("\nProceed with batch fetch for ALL funds? (y/n): ")
    if resp.lower().strip() == "y":
        test_batch_fetch()
    else:
        print("Skipping batch fetch. Run again and enter 'y' to batch fetch.")


if __name__ == "__main__":
    main()
