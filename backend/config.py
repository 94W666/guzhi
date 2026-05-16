"""Application configuration constants."""

import os

# Database
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'data.db')}"

# Eastmoney API base URLs
FUND_LIST_URL = "https://fund.eastmoney.com/data/rankhandler.aspx"
FUND_DETAIL_URL = "https://fund.eastmoney.com/pingzhongdata/{fund_code}.js"
FUND_HOLDINGS_URL = "https://fundf10.eastmoney.com/FundArchivesDatas.aspx"
STOCK_QUOTE_URL = "https://push2.eastmoney.com/api/qt/ulist.np/get"

# Scheduler
STOCK_MARKET_OPEN_HOUR = 21  # UTC+8, US market opens at 21:30 Beijing time
STOCK_MARKET_CLOSE_HOUR = 4   # UTC+8 next day, US market closes at 04:00 Beijing time
NAV_SCRAPE_INTERVAL_MINUTES = 30
