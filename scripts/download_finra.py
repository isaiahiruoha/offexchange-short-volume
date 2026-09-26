"""Download FINRA per-facility short volume files and build the daily panel.

Usage: .venv/bin/python scripts/download_finra.py [start] [end]
"""

import sys
from pathlib import Path

from shortvol import finra

START = sys.argv[1] if len(sys.argv) > 1 else "2016-01-01"
END = sys.argv[2] if len(sys.argv) > 2 else "2026-08-31"
OUT = Path(__file__).resolve().parents[1] / "data" / "interim"

status = finra.download(START, END)
summary = status.pivot_table(index="facility", columns="status", values="date", aggfunc="count")
print(summary.fillna(0).astype(int))

missing = status[status.status == "missing"]
print("\nmissing facility-days by year:")
print(missing.groupby([missing.date.dt.year, "facility"]).size().unstack(fill_value=0))

panel = finra.build_panel(START, END)
panel.to_parquet(OUT / "finra_short_volume.parquet", index=False)
print(f"\npanel: {len(panel):,} rows, {panel.date.nunique()} days, {panel.symbol.nunique():,} symbols")
