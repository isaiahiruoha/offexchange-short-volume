"""Fama-French 12 industry for every S&P 500 ticker in the sample.

Path: ticker -> SEC CIK -> SIC code (SEC submissions API) -> FF12 (Ken French's ranges).
CIKs come from Wikipedia's current-constituents table, then an SEC name search
for departed companies, then an SEC ticker search as a last resort.
"""

from __future__ import annotations

import io
import re
import time
import zipfile

import pandas as pd
import requests

UA = {"User-Agent": "offexchange-short-volume research project"}
FF12_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/Siccodes12.zip"
WIKI = "https://en.wikipedia.org/wiki/"


def ff12_ranges() -> list[tuple[int, int, str]]:
    z = zipfile.ZipFile(io.BytesIO(requests.get(FF12_URL, timeout=30).content))
    text = z.read(z.namelist()[0]).decode("latin-1")
    ranges, name = [], None
    for line in text.splitlines():
        head = re.match(r"\s*\d+\s+(\w+)", line)
        rng = re.match(r"\s*(\d{4})-(\d{4})", line)
        if rng:
            ranges.append((int(rng[1]), int(rng[2]), name))
        elif head:
            name = head[1]
    return ranges


def sic_to_ff12(sic: int | None, ranges) -> str:
    if sic is None:
        return "Other"
    for lo, hi, name in ranges:
        if lo <= sic <= hi:
            return name
    return "Other"  # FF12 defines "Other" as everything not listed


def _get(url: str, **kw) -> requests.Response:
    time.sleep(0.12)  # SEC fair-access limit is 10 requests/second
    return requests.get(url, headers=UA, timeout=30, **kw)


def known_names_and_ciks() -> tuple[dict, dict]:
    """(ticker -> CIK) for current members, (ticker -> company name) for all."""
    current = pd.read_html(io.StringIO(_get(WIKI + "List_of_S%26P_500_companies").text))[0]
    changes = pd.read_html(io.StringIO(_get(WIKI + "Historical_components_of_the_S%26P_500").text))[0]
    changes.columns = ["_".join(c) for c in changes.columns]
    cik = dict(zip(current.Symbol, current.CIK))
    names = dict(zip(current.Symbol, current.Security))
    for tk, nm in zip(changes["Removed_Ticker"], changes["Removed_Security"]):
        if isinstance(tk, str) and isinstance(nm, str):
            names.setdefault(tk, nm)
    return cik, names


def search_cik(name: str) -> int | None:
    r = _get("https://efts.sec.gov/LATEST/search-index", params={"keysTyped": name})
    hits = r.json().get("hits", {}).get("hits", [])
    return int(hits[0]["_id"]) if hits else None


def sic_for(cik: int) -> tuple[int | None, str]:
    j = _get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json").json()
    sic = int(j["sic"]) if j.get("sic") else None
    return sic, j.get("name", "")


def build(sources: pd.DataFrame) -> pd.DataFrame:
    """sources: output of prices.resolve_sources (sp500_ticker, price_ticker)."""
    wiki_cik, names = known_names_and_ciks()
    ranges = ff12_ranges()
    rows = []
    for r in sources.itertuples():
        t, pt = r.sp500_ticker, r.price_ticker
        # Departed tickers can be reused by another company, so for them the
        # company name is a safer key than the ticker.
        if t in wiki_cik or pt in wiki_cik:
            cik, how = wiki_cik.get(t) or wiki_cik.get(pt), "wikipedia"
        elif t in names:
            cik, how = search_cik(names[t]), "sec_name_search"
        else:
            cik, how = search_cik(pt), "sec_ticker_search"
        sic, sec_name = sic_for(int(cik)) if cik else (None, "")
        rows.append((t, names.get(t, ""), cik, sec_name, sic, sic_to_ff12(sic, ranges), how))
    out = pd.DataFrame(
        rows, columns=["sp500_ticker", "name", "cik", "sec_name", "sic", "ff12", "cik_source"]
    )
    out["name_check"] = [_same_company(a, b) for a, b in zip(out.name, out.sec_name)]
    return out


def _same_company(a: str, b: str) -> bool:
    """Loose check that two company names share their first real word."""
    def first(s):
        words = re.findall(r"[a-z0-9]+", s.lower())
        words = [w for w in words if w not in {"the", "inc", "corp", "co"}]
        return words[0] if words else ""
    return bool(a) and bool(b) and first(a) == first(b)
