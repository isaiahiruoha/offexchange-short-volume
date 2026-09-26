"""Daily prices for the point-in-time S&P 500 universe.

yfinance is the primary source but silently drops delisted tickers, so names it
cannot serve come from Tiingo (free tier: 50 requests/hour, 500 symbols/month).
Renamed and bankrupt tickers resolve through reference/ticker_map.csv.

Both sources are normalized to one schema with RAW (as-traded) prices and volume,
because FINRA volumes are raw share counts, plus a split-and-dividend adjusted
close for close-to-close returns.
"""

from __future__ import annotations

import logging
import os
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
MEMBERSHIP_URL = (
    "https://raw.githubusercontent.com/fja05680/sp500/master/sp500_ticker_start_end.csv"
)
SCHEMA = ["date", "open", "high", "low", "close", "adj_close", "volume"]


def load_membership(start: str, end: str) -> pd.DataFrame:
    """Ticker spells that overlap [start, end]. Cached under data/raw."""
    path = RAW_DIR / "sp500_ticker_start_end.csv"
    if not path.exists():
        path.write_bytes(requests.get(MEMBERSHIP_URL, timeout=30).content)
    m = pd.read_csv(path, parse_dates=["start_date", "end_date"])
    return m[(m.start_date <= end) & (m.end_date.isna() | (m.end_date >= start))].reset_index(
        drop=True
    )


def load_ticker_map() -> pd.DataFrame:
    return pd.read_csv(ROOT / "reference" / "ticker_map.csv", keep_default_na=False)


def _unsplit(df: pd.DataFrame, splits: pd.Series) -> pd.DataFrame:
    """Undo yfinance split adjustment. A split on day s scales every row before s."""
    ratio = splits.replace(0, 1).fillna(1)
    later = ratio[::-1].cumprod()[::-1].shift(-1, fill_value=1.0)
    out = df.copy()
    for c in ["open", "high", "low", "close"]:
        out[c] = df[c] * later
    out["volume"] = (df["volume"] / later).round()
    return out


def fetch_yfinance(ticker: str, start: str, end: str) -> pd.DataFrame:
    import yfinance as yf

    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        h = yf.Ticker(ticker.replace(".", "-")).history(
            start=start, end=end, auto_adjust=False, actions=True
        )
    if h.empty:
        return pd.DataFrame(columns=SCHEMA)
    h.index = h.index.tz_localize(None).normalize()
    df = h.rename(
        columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Adj Close": "adj_close",
            "Volume": "volume",
        }
    )
    df = _unsplit(df, h["Stock Splits"])
    return df.rename_axis("date").reset_index()[SCHEMA]


def fetch_tiingo(ticker: str, start: str, end: str) -> pd.DataFrame:
    key = os.environ["TIINGO_API_KEY"]
    url = f"https://api.tiingo.com/tiingo/daily/{ticker}/prices"
    for attempt in range(3):
        r = requests.get(
            url,
            params={"startDate": start, "endDate": end},
            headers={"Authorization": f"Token {key}"},
            timeout=60,
        )
        if r.status_code == 429:
            time.sleep(600 * (attempt + 1))
            continue
        break
    if r.status_code == 404:
        return pd.DataFrame(columns=SCHEMA)
    r.raise_for_status()
    data = r.json()
    if not data:
        return pd.DataFrame(columns=SCHEMA)
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None).dt.normalize()
    df = df.rename(columns={"adjClose": "adj_close"})
    return df[SCHEMA]


def load_env() -> None:
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def resolve_sources(membership: pd.DataFrame, yf_available: set[str]) -> pd.DataFrame:
    """Decide where each S&P ticker's history comes from.

    Order: explicit map entry, then yfinance under the same ticker, then Tiingo.
    """
    tmap = load_ticker_map().set_index("sp500_ticker")
    rows = []
    for t in sorted(membership.ticker.unique()):
        if t in tmap.index:
            e = tmap.loc[t]
            rows.append((t, e.price_ticker or None, e.source, e.relation))
        elif t in yf_available:
            rows.append((t, t, "yfinance", "same"))
        else:
            rows.append((t, t, "tiingo", "delisted"))
    return pd.DataFrame(rows, columns=["sp500_ticker", "price_ticker", "source", "relation"])


def cache_path(source: str, ticker: str) -> Path:
    return RAW_DIR / "prices" / source / f"{ticker}.parquet"


def fetch_cached(source: str, ticker: str, start: str, end: str) -> tuple[pd.DataFrame, bool]:
    """Returns (frame, was_network_call)."""
    path = cache_path(source, ticker)
    if path.exists():
        return pd.read_parquet(path), False
    fn = fetch_yfinance if source == "yfinance" else fetch_tiingo
    df = fn(ticker, start, end)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    return df, True


def spell_coverage(sources: pd.DataFrame, membership: pd.DataFrame, days: pd.DatetimeIndex):
    """Share of each ticker's in-index trading days that have a price row.

    Low coverage usually means the ticker now belongs to a different company
    (e.g. yfinance "FB" is not Meta), so the history needs a rename-map entry.
    """
    src = sources.set_index("sp500_ticker")
    rows = []
    for m in membership.itertuples():
        end = m.end_date if pd.notna(m.end_date) else days[-1]
        spell = days[(days >= m.start_date) & (days <= end)]
        if not len(spell) or m.ticker not in src.index:
            continue
        s = src.loc[m.ticker]
        path = cache_path(s.source, s.price_ticker) if s.price_ticker else None
        have = pd.read_parquet(path, columns=["date"]).date if path and path.exists() else []
        covered = spell.isin(pd.DatetimeIndex(have)).mean()
        rows.append((m.ticker, s.price_ticker, s.source, len(spell), round(covered, 3)))
    return pd.DataFrame(rows, columns=["sp500_ticker", "price_ticker", "source", "days", "coverage"])


def intraday_return(df: pd.DataFrame) -> pd.Series:
    """open(t) to close(t). Raw prices are fine: no split or dividend inside a session."""
    return df["close"] / df["open"] - 1


def close_return(df: pd.DataFrame) -> pd.Series:
    return df["adj_close"].pct_change(fill_method=None)


def log_dollar_volume(df: pd.DataFrame) -> pd.Series:
    return np.log1p(df["close"] * df["volume"])
