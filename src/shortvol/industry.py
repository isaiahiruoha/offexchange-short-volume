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


STOPWORDS = {"the", "inc", "corp", "corporation", "co", "company", "companies", "plc", "ltd",
             "holdings", "group", "incorporated", "class", "a", "b", "c", "de"}


def _core_words(name: str) -> list[str]:
    name = re.sub(r"\(.*?\)", " ", name.lower()).replace("'", "").replace("’", "")
    return [w for w in re.findall(r"[a-z0-9&]+", name) if w not in STOPWORDS]


def _search(query: str) -> list[dict]:
    for attempt in range(4):
        r = _get("https://efts.sec.gov/LATEST/search-index", params={"keysTyped": query})
        if r.ok and "hits" in r.json():
            return [{"cik": int(h["_id"]), **h["_source"]} for h in r.json()["hits"]["hits"]]
        time.sleep(2**attempt)
    raise RuntimeError(f"SEC search failed for {query!r}")


def name_candidates(name: str) -> list[int]:
    """SEC entities whose name starts like this company's name (spaces ignored)."""
    key = "".join(_core_words(name))[:6]
    if not key:
        return []
    hits = _search(" ".join(_core_words(name)[:2]))
    return [h["cik"] for h in hits if "".join(_core_words(h.get("entity", ""))).startswith(key)]


def search_by_ticker(ticker: str) -> int | None:
    """SEC entity currently listed under exactly this ticker."""
    for hit in _search(ticker):
        if ticker in (hit.get("tickers") or "").split(", "):
            return hit["cik"]
    return None


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
            sic, sec_name = sic_for(int(cik))
        else:
            # Name matches include funds and shells with no SIC; take the first real company.
            candidates = name_candidates(names[t]) if t in names else []
            candidates.append(search_by_ticker(pt))
            cik, sic, sec_name, how = None, None, "", "unresolved"
            for c in filter(None, candidates):
                sic, sec_name = sic_for(c)
                if sic:
                    cik, how = c, "sec_search"
                    break
        rows.append((t, names.get(t, ""), cik, sec_name, sic, sic_to_ff12(sic, ranges), how))
    return pd.DataFrame(
        rows, columns=["sp500_ticker", "name", "cik", "sec_name", "sic", "ff12", "cik_source"]
    )

