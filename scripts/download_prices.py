"""Download daily prices for every S&P 500 member between START and END.

yfinance names go first (no rate limit). Tiingo names are paced to the free
tier's 50 requests/hour; the script is resumable because every ticker is cached.

Usage: .venv/bin/python scripts/download_prices.py [yfinance|tiingo|all]
"""

import sys
import time

import pandas as pd

from shortvol import prices

START, END = "2015-10-01", "2026-09-01"  # lead-in for 60-day windows
WHICH = sys.argv[1] if len(sys.argv) > 1 else "all"
TIINGO_PACE_SECONDS = 75  # 48 requests/hour, under the 50/hour limit

prices.load_env()
membership = prices.load_membership("2016-01-01", "2026-08-31")

# Probe yfinance for every member ticker; empty results mean "try Tiingo".
yf_ok = set()
for t in sorted(membership.ticker.unique()):
    df, _ = prices.fetch_cached("yfinance", t, START, END)
    if len(df):
        yf_ok.add(t)
sources = prices.resolve_sources(membership, yf_ok)
sources.to_csv(prices.RAW_DIR / "price_sources.csv", index=False)
print(sources.groupby(["source", "relation"]).size().to_string(), flush=True)

for row in sources.itertuples():
    if not row.price_ticker or row.source == "none":
        continue
    if WHICH not in ("all", row.source):
        continue
    df, networked = prices.fetch_cached(row.source, row.price_ticker, START, END)
    print(f"{row.sp500_ticker:6} -> {row.price_ticker:6} {row.source:8} {len(df):5} rows", flush=True)
    if networked and row.source == "tiingo":
        time.sleep(TIINGO_PACE_SECONDS)

empty = [
    r.sp500_ticker
    for r in sources.itertuples()
    if r.price_ticker
    and r.source != "none"
    and prices.cache_path(r.source, r.price_ticker).exists()
    and pd.read_parquet(prices.cache_path(r.source, r.price_ticker)).empty
]
print(f"\nempty after fetch ({len(empty)}): {empty}")
