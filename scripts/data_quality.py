"""Data-quality numbers for the raw-data slides. Uses short volume and volume only, no returns."""

import numpy as np
import pandas as pd

from shortvol import prices

df = pd.read_parquet(prices.ROOT / "data" / "processed" / "panel.parquet")
df["svr"] = df.short_volume / df.total_volume
df["off_exchange_share"] = df.total_volume / df.volume
df["dollar_volume"] = df.close * df.volume
df["size_tercile"] = df.groupby("date").dollar_volume.transform(
    lambda x: pd.qcut(x.rank(method="first"), 3, labels=["small", "mid", "large"])
)
df["year"] = df.date.dt.year


def section(title):
    print(f"\n== {title}")


section("Coverage")
per_day = df.groupby("date").size()
print(f"stock-days {len(df):,}, stocks {df.ticker.nunique()}, stocks per day min {per_day.min()} median {per_day.median():.0f}")
no_finra = df.short_volume.isna()
print(f"no FINRA row: {no_finra.mean():.2%} of stock-days")
print("no FINRA row by size tercile:", no_finra.groupby(df.size_tercile, observed=True).mean().map("{:.2%}".format).to_dict())
print(f"price-source volume missing: {df.volume.isna().sum()} stock-days")
below = df.total_volume < 10_000
print(f"below the 10k off-exchange floor: {below.mean():.3%} of stock-days")

section("One observation")
row = df[(df.ticker == "AAPL") & (df.date == "2023-03-07")]
print(row[["date", "ticker", "short_volume", "short_exempt_volume", "total_volume",
           "TotalVolume_Q", "TotalVolume_N", "TotalVolume_B", "volume", "open", "close"]].T.to_string())

section("Short volume ratio (SVR)")
ok = df[~no_finra & ~below]
print(ok.svr.describe(percentiles=[0.01, 0.25, 0.5, 0.75, 0.99]).round(3).to_string())
print("mean SVR by size tercile:", ok.groupby("size_tercile", observed=True).svr.mean().round(3).to_dict())
print("mean SVR by year:", ok.groupby("year").svr.mean().round(3).to_dict())

section("Where the SVR variance is")
stock_mean = ok.groupby("ticker").svr.transform("mean")
total = ok.svr.var()
between = stock_mean.var()
print(f"between stocks (persistent level): {between / total:.0%}, within stock over time: {1 - between / total:.0%}")
ok = ok.sort_values(["ticker", "date"])
lag = ok.groupby("ticker").svr.shift(1)
print(f"day-to-day autocorrelation of SVR: {ok.svr.corr(lag):.2f}")

section("Off-exchange share (FINRA volume / consolidated volume)")
print(ok.off_exchange_share.describe(percentiles=[0.01, 0.5, 0.99]).round(3).to_string())
print("median by year:", ok.groupby("year").off_exchange_share.median().round(3).to_dict())
print("median by size tercile:", ok.groupby("size_tercile", observed=True).off_exchange_share.median().round(3).to_dict())
impossible = (ok.off_exchange_share > 1).mean()
print(f"share > 1 (FINRA volume above consolidated): {impossible:.3%} of stock-days")

section("Facility mix (share of FINRA volume)")
fac = ok.filter(like="TotalVolume_").fillna(0)
mix = fac.groupby(ok.year).sum()
print((mix.div(mix.sum(axis=1), axis=0) * 100).round(1).to_string())

section("Price-source validation")
agree = pd.read_csv(prices.ROOT / "data" / "processed" / "volume_agreement.csv")
print(f"median quarterly volume correlation: {agree['corr'].median():.2f}")
print("wrong-company quarters dropped:", agree.wrong_company.sum(), sorted(agree[agree.wrong_company].ticker.unique()))
print("source mix (stock-days):", df.source.value_counts().to_dict())
print(f"days with open or close missing or <= 0: {((df.open <= 0) | (df.close <= 0) | df.open.isna()).sum()}")
extreme = (np.abs(df.close / df.open - 1) > 0.5).sum()
print(f"open-to-close moves above 50%: {extreme}")
