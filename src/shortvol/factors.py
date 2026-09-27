"""Daily Fama-French factors from Ken French's data library (percent converted to decimals)."""

from __future__ import annotations

import io
import zipfile

import pandas as pd
import requests

BASE = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
FILES = [
    "F-F_Research_Data_5_Factors_2x3_daily_CSV.zip",  # Mkt-RF, SMB, HML, RMW, CMA, RF
    "F-F_Momentum_Factor_daily_CSV.zip",  # Mom
    "F-F_ST_Reversal_Factor_daily_CSV.zip",  # ST_Rev (prior month's losers minus winners)
]


def _read(name: str) -> pd.DataFrame:
    z = zipfile.ZipFile(io.BytesIO(requests.get(BASE + name, timeout=60).content))
    lines = z.read(z.namelist()[0]).decode("latin-1").splitlines()
    header = next(i for i, line in enumerate(lines) if line.startswith(","))
    rows = [line for line in lines[header + 1:] if line.strip()[:8].isdigit()]
    df = pd.read_csv(io.StringIO("\n".join([lines[header]] + rows)), index_col=0)
    df.index = pd.to_datetime(df.index.astype(str), format="%Y%m%d")
    df.columns = df.columns.str.strip()
    return df / 100


def load() -> pd.DataFrame:
    return pd.concat([_read(f) for f in FILES], axis=1, join="inner")
