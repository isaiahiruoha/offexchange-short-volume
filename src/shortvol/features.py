"""Signals, controls and targets, one row per stock per day.

Everything at row t uses information available by FINRA's ~17:18 ET post on day t.
Targets are the next tradable returns: open(t+1) to close(t+1), and close(t+1) to close(t+2).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

FLOOR = 10_000  # minimum off-exchange shares on day t (pre-registered)


def _consecutive(df: pd.DataFrame, lag: int) -> pd.Series:
    """True where the row `lag` rows back is exactly `lag` trading days back.

    The panel has gaps (index exits, dropped quarters); windows must not span them.
    """
    return df.groupby("ticker").day.diff(lag) == lag


def add_all(df: pd.DataFrame, days: pd.DatetimeIndex, v0: float | None = None) -> pd.DataFrame:
    df = df.sort_values(["ticker", "date"]).reset_index(drop=True)
    df["day"] = days.get_indexer(df.date)
    g = df.groupby("ticker")

    # Signals. Days under the floor are treated as missing.
    thin = df.total_volume < FLOOR
    sv = df.short_volume.mask(thin)
    tv = df.total_volume.mask(thin)
    df["svr1"] = sv / tv
    ok5 = _consecutive(df, 4)
    df["sv5"] = sv.groupby(df.ticker).transform(lambda s: s.rolling(5).sum()).where(ok5)
    df["tv5"] = tv.groupby(df.ticker).transform(lambda s: s.rolling(5).sum()).where(ok5)
    df["svr5"] = df.sv5 / df.tv5
    svr1 = df.groupby("ticker").svr1
    df["svr_base"] = svr1.transform(lambda s: s.shift(6).rolling(60, min_periods=40).mean())
    df["svr_abnormal"] = df.svr5 - df.svr_base
    df["svr_mean60"] = svr1.transform(lambda s: s.rolling(60, min_periods=40).mean())
    if v0 is not None:
        w = df.tv5 / (df.tv5 + v0)
        df["svr5_shrunk"] = w * df.svr5 + (1 - w) * df.svr_mean60

    # Controls.
    df["ret1"] = g.adj_close.pct_change(fill_method=None).where(_consecutive(df, 1))
    df["ret5"] = g.adj_close.pct_change(5, fill_method=None).where(_consecutive(df, 5))
    dollar_volume = df.close * df.volume
    df["log_adv20"] = np.log(dollar_volume.groupby(df.ticker).transform(
        lambda s: s.rolling(20, min_periods=15).mean()))
    avg_volume = g.volume.transform(lambda s: s.rolling(20, min_periods=15).mean())
    df["abnormal_volume"] = df.volume / avg_volume
    share = df.total_volume / df.volume
    df["off_exchange_share"] = share.where(share <= 1)  # > 1 is a price-source volume error

    # Targets.
    next_ok = g.day.shift(-1) - df.day == 1
    df["fwd_oc"] = (g.close.shift(-1) / g.open.shift(-1) - 1).where(next_ok)
    both_ok = next_ok & (g.day.shift(-2) - df.day == 2)
    df["fwd_cc"] = (g.adj_close.shift(-2) / g.adj_close.shift(-1) - 1).where(both_ok)
    return df


def estimate_v0(df: pd.DataFrame, end: str = "2019-12-31", buckets: int = 20) -> dict:
    """Volume at which SVR5 noise equals SVR5's real variation around the stock's own average.

    Model: var(SVR5 - own baseline | volume V) = s2 + c / V, where s2 is real variation
    and c / V is sampling noise that shrinks with volume. Fitted by OLS across volume
    buckets. V0 = c / s2, so the shrinkage weight V / (V + V0) = s2 / (s2 + c / V).
    Uses short volume only, never returns.
    """
    d = df[(df.date <= end)].dropna(subset=["svr_abnormal", "tv5"])
    d = d.assign(bucket=pd.qcut(d.tv5, buckets, labels=False))
    b = d.groupby("bucket").agg(var=("svr_abnormal", "var"), inv_v=("tv5", lambda v: (1 / v).mean()))
    c, s2 = np.polyfit(b.inv_v, b["var"], 1)
    return {"v0": c / s2, "c": c, "s2": s2, "buckets": b}
