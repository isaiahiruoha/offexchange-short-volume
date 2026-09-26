"""Stock-day panel: S&P 500 membership x prices x FINRA short volume.

Price histories are validated against FINRA: the same stock's off-exchange volume
and total volume move together day to day (quarterly log-volume correlation is
usually 0.8-0.9). A quarter below MIN_VOLUME_CORR means the price source is serving
a different company under that ticker, so that ticker-quarter is dropped.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from shortvol import prices

MIN_VOLUME_CORR = 0.5
MIN_DAYS_TO_TEST = 20


def finra_symbol(ticker: str) -> str:
    """Membership lists write class shares as BRK.B; FINRA writes BRK/B."""
    return ticker.replace(".", "/")


def membership_days(membership: pd.DataFrame, days: pd.DatetimeIndex) -> pd.DataFrame:
    rows = []
    for m in membership.itertuples():
        end = m.end_date if pd.notna(m.end_date) else days[-1]
        d = days[(days >= m.start_date) & (days <= end)]
        rows.append(pd.DataFrame({"date": d, "ticker": m.ticker}))
    return pd.concat(rows, ignore_index=True).drop_duplicates()


def load_prices(sources: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for s in sources.itertuples():
        path = prices.cache_path(s.source, s.price_ticker) if s.price_ticker else None
        if path and path.exists():
            df = pd.read_parquet(path)
            if len(df):
                frames.append(df.assign(ticker=s.sp500_ticker, source=s.source))
    return pd.concat(frames, ignore_index=True)


def volume_agreement(panel: pd.DataFrame) -> pd.DataFrame:
    """Quarterly correlation of log FINRA volume vs log price-source volume."""
    ok = panel[(panel.total_volume > 0) & (panel.volume > 0)].copy()
    ok["a"], ok["b"] = np.log(ok.total_volume), np.log(ok.volume)
    ok["quarter"] = ok.date.dt.to_period("Q")
    g = ok.groupby(["ticker", "quarter"])
    return pd.DataFrame({"days": g.size(), "corr": g.apply(lambda x: x.a.corr(x.b))}).reset_index()


def build(membership, sources, finra_path, days) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (panel, per ticker-quarter volume agreement)."""
    base = membership_days(membership, days)
    px = load_prices(sources)
    panel = base.merge(px, on=["date", "ticker"], how="inner")

    symbols = {finra_symbol(t): t for t in panel.ticker.unique()}
    fin = pd.read_parquet(finra_path, filters=[("symbol", "in", list(symbols))])
    fin["ticker"] = fin.symbol.map(symbols)
    panel = panel.merge(fin.drop(columns="symbol"), on=["date", "ticker"], how="left")

    agree = volume_agreement(panel)
    bad = agree[(agree.days >= MIN_DAYS_TO_TEST) & (agree["corr"] < MIN_VOLUME_CORR)]
    panel["quarter"] = panel.date.dt.to_period("Q")
    drop = panel.set_index(["ticker", "quarter"]).index.isin(bad.set_index(["ticker", "quarter"]).index)
    return panel[~drop].drop(columns="quarter").reset_index(drop=True), agree
