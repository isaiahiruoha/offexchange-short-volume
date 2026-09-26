# Data Findings (verified 2026-09-26)

Everything here was checked live against the source.

## FINRA Reg SHO daily short volume

### History and file layout

The consolidated `CNMSshvolYYYYMMDD.txt` file on `cdn.finra.org` only goes back to about 2018-08.
Requests for earlier dates return 403 AccessDenied.
The CNMS file alone cannot cover a 2016-2026 sample.

Per-facility files go back to 2009-11-10:

| Prefix | Facility | Market code | Available from |
|---|---|---|---|
| `FNSQshvol` | Nasdaq TRF Carteret | Q | 2009-11 |
| `FNYXshvol` | NYSE TRF | N | 2009-11 |
| `FNQCshvol` | Nasdaq TRF Chicago | B | 2018-08-01 (empty at launch) |
| `FNRAshvol` | ADF | D | 2009-11, some days missing (403) |
| `FORFshvol` | ORF (OTC, non-NMS) | - | 2009-11, not part of CNMS |

CNMS equals the sum of the NMS facility files.
Check on 2023-03-07, AAPL: Q 5,029,587 + N 4,117,018 + B 56,377 = 9,202,982, which matches CNMS exactly.
So the full 2016-2026 panel is rebuilt by summing Q + N + B (+ D) per symbol per day.
This gives one consistent construction across the whole sample, with no switch between file types.

Structural break: Nasdaq TRF Chicago (B) only exists from 2018-08.
It is small (about 0.5% of AAPL's off-exchange volume on 2023-03-07), but it should be named as a known discontinuity.

### Publication time

The CDN `Last-Modified` header on recent files is consistently about 17:18 ET on the trade date:

- 2026-09-18 to 2026-09-25: 21:18 GMT (EDT), which is 17:18 ET
- 2025-01-02 and 2023-03-07: 22:17 GMT (EST), which is 17:17 ET

This is after the 16:00 close and well before the next 09:30 open.
The tradable target is therefore open(t+1) to close(t+1).
close(t) to close(t+1) would be look-ahead.

Caveat: files dated before about 2021 have `Last-Modified` stamps from 2021 (for example, 2019-01-02 shows 2021-10-27).
They were re-uploaded, so the original publication time cannot be verified for the early sample, and silent restatement cannot be ruled out.

### FINRA Query API

`api.finra.org/.../regShoDaily` without authentication returns only recent data (2026 rows).
Filtering on 2010, 2016 or 2018 dates returns nothing.
The CDN per-facility files are the history source.

## Prices and universe

### Survivorship in yfinance

yfinance returns no data at all for delisted tickers.
Tested: TWTR, XLNX, CELG, ATVI, SIVB, FRC, LLTC, MON all return 0 rows.

Scale of the problem for a point-in-time S&P 500 universe, 2016-01 to 2026-08:

- 745 unique tickers were members at some point
- 242 of them are no longer members
- 133 of those 242 have no yfinance data at all, which is about 18% of all names ever in the universe

The missing names are mostly acquisition targets and failures (SIVB, FRC).
These are the stocks where short-selling informativeness should matter most.
Dropping them biases the test.

A second risk is ticker reuse: some of the 109 "recovered" names may be a different company that later took the same symbol.
This has to be checked with company names or start dates, not just ticker strings.

### Point-in-time membership

`fja05680/sp500` is current: the last snapshot is dated 2026-08-18.
`sp500_ticker_start_end.csv` gives ticker spells, which is enough for a daily membership mask.
