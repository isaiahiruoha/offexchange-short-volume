"""FINRA Reg SHO daily short sale volume.

The consolidated CNMS file only exists from about 2018-08, so the panel is rebuilt
from the per-facility files, which go back to 2009-11. CNMS equals the sum of the
NMS facility files (verified on 2023-03-07), so this construction is consistent
across the whole sample. See docs/data_findings.md.
"""

from __future__ import annotations

import io
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import pandas_market_calendars as mcal
import requests

CDN = "https://cdn.finra.org/equity/regsho/daily/{prefix}shvol{date:%Y%m%d}.txt"

# NMS trade reporting facilities that make up CNMS. ORF (FORF) is OTC and excluded.
FACILITIES = {
    "FNSQ": "Q",  # Nasdaq TRF Carteret
    "FNYX": "N",  # NYSE TRF
    "FNQC": "B",  # Nasdaq TRF Chicago, from 2018-08-01
    "FNRA": "D",  # ADF, sparse
}

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw" / "finra"

COLUMNS = ["Date", "Symbol", "ShortVolume", "ShortExemptVolume", "TotalVolume", "Market"]


def trading_days(start: str, end: str) -> pd.DatetimeIndex:
    nyse = mcal.get_calendar("NYSE")
    return nyse.valid_days(start, end).tz_localize(None)


def _raw_path(prefix: str, date: pd.Timestamp) -> Path:
    return RAW_DIR / prefix / f"{prefix}shvol{date:%Y%m%d}.txt"


def _missing_marker(prefix: str, date: pd.Timestamp) -> Path:
    return RAW_DIR / prefix / f"{prefix}shvol{date:%Y%m%d}.missing"


def fetch_file(session: requests.Session, prefix: str, date: pd.Timestamp) -> str:
    """Download one facility-day file into the raw cache.

    Returns "cached", "ok" or "missing". A 403 from the CDN means the file does not
    exist; that is recorded with a marker so reruns do not re-request it.
    """
    path, marker = _raw_path(prefix, date), _missing_marker(prefix, date)
    if path.exists() or marker.exists():
        return "cached"
    path.parent.mkdir(parents=True, exist_ok=True)
    url = CDN.format(prefix=prefix, date=date)
    for attempt in range(4):
        try:
            r = session.get(url, timeout=30)
        except requests.RequestException:
            time.sleep(2**attempt)
            continue
        if r.status_code == 200:
            path.write_bytes(r.content)
            return "ok"
        if r.status_code in (403, 404):
            marker.touch()
            return "missing"
        time.sleep(2**attempt)
    raise RuntimeError(f"failed to fetch {url}")


def download(start: str, end: str, workers: int = 8) -> pd.DataFrame:
    """Fetch every facility file for every NYSE trading day in [start, end]."""
    days = trading_days(start, end)
    jobs = [(p, d) for d in days for p in FACILITIES]
    status = []
    with requests.Session() as session, ThreadPoolExecutor(workers) as pool:
        futures = {pool.submit(fetch_file, session, p, d): (p, d) for p, d in jobs}
        for f in as_completed(futures):
            p, d = futures[f]
            status.append((d, p, f.result()))
    return pd.DataFrame(status, columns=["date", "facility", "status"])


def read_file(path: Path) -> pd.DataFrame:
    """Parse one facility file. The last line is a record count trailer, not data."""
    # keep_default_na=False: real tickers like "NA" and "NAN" must not become NaN.
    text = path.read_text()
    df = pd.read_csv(io.StringIO(text), sep="|", dtype=str, keep_default_na=False)
    df = df[df["Date"].str.fullmatch(r"\d{8}", na=False)]
    return df[COLUMNS]


def build_panel(start: str, end: str) -> pd.DataFrame:
    """Sum facility files into one row per (date, symbol).

    Keeps per-facility total volume so the Chicago TRF break (2018-08) and facility
    mix can be examined later.
    """
    frames = []
    for d in trading_days(start, end):
        for prefix, code in FACILITIES.items():
            path = _raw_path(prefix, d)
            if path.exists():
                df = read_file(path)
                df["facility"] = code
                frames.append(df)
    raw = pd.concat(frames, ignore_index=True)
    raw["date"] = pd.to_datetime(raw["Date"], format="%Y%m%d")
    for c in ["ShortVolume", "ShortExemptVolume", "TotalVolume"]:
        raw[c] = pd.to_numeric(raw[c], errors="coerce")

    panel = raw.groupby(["date", "Symbol"], sort=True)[
        ["ShortVolume", "ShortExemptVolume", "TotalVolume"]
    ].sum()
    by_fac = raw.pivot_table(
        index=["date", "Symbol"], columns="facility", values="TotalVolume", aggfunc="sum"
    ).add_prefix("TotalVolume_")
    panel = panel.join(by_fac).reset_index()
    return panel.rename(
        columns={
            "Symbol": "symbol",
            "ShortVolume": "short_volume",
            "ShortExemptVolume": "short_exempt_volume",
            "TotalVolume": "total_volume",
        }
    )
