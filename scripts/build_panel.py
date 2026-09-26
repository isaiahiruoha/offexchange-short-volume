"""Build data/processed/panel.parquet: one row per S&P 500 member per trading day."""

import pandas as pd

from shortvol import finra, panel, prices

START, END = "2016-01-01", "2026-08-31"
OUT = prices.ROOT / "data" / "processed"

membership = prices.load_membership(START, END)
sources = pd.read_csv(prices.RAW_DIR / "price_sources.csv", keep_default_na=False)
days = finra.trading_days(START, END)
industry = pd.read_csv(prices.ROOT / "reference" / "industry.csv")[["sp500_ticker", "ff12"]]

df, agree = panel.build(
    membership, sources, prices.ROOT / "data" / "interim" / "finra_short_volume.parquet", days
)
df = df.merge(industry.rename(columns={"sp500_ticker": "ticker"}), on="ticker", how="left")
df.to_parquet(OUT / "panel.parquet", index=False)
agree.to_csv(OUT / "volume_agreement.csv", index=False)

expected = len(panel.membership_days(membership, days))
bad = agree[agree.wrong_company]
print(f"member stock-days: {expected:,}")
print(f"in panel:          {len(df):,} ({len(df) / expected:.1%})")
print(f"ticker-quarters: {len(agree):,}, dropped as wrong company: {len(bad)}")
print(f"tickers affected: {bad.ticker.nunique()} {sorted(bad.ticker.unique())}")
print(f"stock-days without a FINRA row: {df.short_volume.isna().sum():,}")
