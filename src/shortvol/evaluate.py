"""Pre-registered evaluation: ranking, neutralization, IC, quintile spreads, decay, splits."""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import norm

MIN_STOCKS = 50  # skip days with too few stocks for a cross-sectional statistic


def gauss_rank(x: pd.Series, dates: pd.Series) -> pd.Series:
    """Rank within each day, map to a standard normal, clip at the 1st/99th percentile."""
    r = x.groupby(dates).rank()
    n = r.groupby(dates).transform("count")
    z = pd.Series(norm.ppf((r - 0.5) / n), index=x.index)
    return z.clip(norm.ppf(0.01), norm.ppf(0.99))


def neutralize(df: pd.DataFrame, signal: str, controls: list[str], industry: str | None = "ff12"):
    """Residual of the Gaussian-ranked signal on Gaussian-ranked controls and industry dummies, per day."""
    cols = [signal] + controls + ([industry] if industry else [])
    d = df[["date"] + cols].dropna()
    y = gauss_rank(d[signal], d.date)
    X = pd.concat({c: gauss_rank(d[c], d.date) for c in controls}, axis=1)
    if industry:
        X = X.join(pd.get_dummies(d[industry], prefix="ind", dtype=float))
    else:
        X["const"] = 1.0
    out = pd.Series(np.nan, index=df.index)
    for idx in d.groupby("date").groups.values():
        if len(idx) < MIN_STOCKS:
            continue
        beta, *_ = np.linalg.lstsq(X.loc[idx].values, y.loc[idx].values, rcond=None)
        out.loc[idx] = y.loc[idx].values - X.loc[idx].values @ beta
    return out


def daily_ic(df: pd.DataFrame, signal: str, target: str) -> pd.Series:
    """Spearman rank correlation between signal and target, one value per day."""
    d = df[["date", signal, target]].dropna()
    d = d[d.groupby("date").date.transform("size") >= MIN_STOCKS]
    ranks = d.groupby("date")[[signal, target]].rank()
    return ranks[signal].groupby(d.date).corr(ranks[target])


def newey_west_t(x: pd.Series, lags: int = 5) -> float:
    x = x.dropna()
    fit = sm.OLS(x.values, np.ones(len(x))).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return float(fit.tvalues[0])


def summarize_ic(ic: pd.Series) -> dict:
    return {
        "mean_ic": ic.mean(),
        "nw_t": newey_west_t(ic),
        "ic_ir_annual": ic.mean() / ic.std() * np.sqrt(252),
        "pct_positive": (ic > 0).mean(),
        "days": ic.count(),
    }


def quintile_spread(df: pd.DataFrame, signal: str, target: str) -> dict:
    """Equal-weight top-minus-bottom quintile of the signal, with turnover and break-even cost.

    The sign follows the signal: a negative spread means low-signal stocks outperformed.
    Break-even cost is the one-way trading cost (bps) that would erase the gross spread.
    """
    d = df[["date", "ticker", signal, target]].dropna(subset=[signal])
    d = d[d.groupby("date").date.transform("size") >= MIN_STOCKS]
    q = d.groupby("date")[signal].transform(lambda s: pd.qcut(s.rank(method="first"), 5, labels=False))
    leg = np.where(q == 4, 1.0, np.where(q == 0, -1.0, 0.0))
    d = d.assign(leg=leg)
    d["w"] = d.leg / d.groupby(["date", "leg"]).leg.transform("size")
    d.loc[d.leg == 0, "w"] = 0.0
    spread = (d.w * d[target]).groupby(d.date).sum(min_count=1)
    weights = d.pivot_table(index="date", columns="ticker", values="w", fill_value=0.0)
    turnover = weights.diff().abs().sum(axis=1).iloc[1:]
    mean_spread = spread.mean()
    return {
        "spread_bps": mean_spread * 1e4,
        "spread_nw_t": newey_west_t(spread),
        "turnover": turnover.mean(),
        "breakeven_bps": abs(mean_spread) / turnover.mean() * 1e4,
    }


def shift_target(df: pd.DataFrame, target: str, k: int) -> pd.Series:
    """Target k-1 trading days further ahead (k=1 is the target itself), respecting gaps."""
    if k == 1:
        return df[target]
    g = df.groupby("ticker")
    ok = g.day.shift(-(k - 1)) - df.day == k - 1
    return g[target].shift(-(k - 1)).where(ok)


def ic_by_group(df: pd.DataFrame, signal: str, target: str, group: str) -> pd.DataFrame:
    """IC computed within each group (e.g. size tercile) each day, then summarized."""
    rows = {}
    for name, g in df.groupby(group, observed=True):
        ic = daily_ic(g, signal, target)
        if ic.count() > 20:
            rows[name] = summarize_ic(ic)
    return pd.DataFrame(rows).T


def terciles(df: pd.DataFrame, col: str, labels: list[str]) -> pd.Series:
    """Split stocks into terciles of `col` each day; days with too few values get NaN."""
    def cut(x):
        if x.count() < MIN_STOCKS:
            return pd.Series(np.nan, index=x.index)
        return pd.qcut(x.rank(method="first"), 3, labels=labels).astype(object)
    return df.groupby("date")[col].transform(cut)
