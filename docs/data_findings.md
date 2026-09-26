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

### Recovering the missing 133 (Tiingo free tier + rename map)

The 133 split into three groups:

| Group | Count | Resolution |
|---|---|---|
| Truly delisted, still under the old ticker in Tiingo | 92 | Tiingo `supported_tickers.csv` spans the full S&P window |
| Renamed, history lives under the new ticker | ~34 | `reference/ticker_map.csv`, fetched from yfinance or Tiingo |
| Bankrupt, history continues under an OTC ticker | 4 | SIVB to SIVBQ, FRC to FRCB, ENDP to ENDPQ, MNK to MNKKQ (Tiingo) |
| Unrecoverable | 2 | CCE (merged into a different entity, CCEP), ESV (VAL before 2017 is Valspar, a recycled ticker) |

So about 131 of 133 are recoverable, and the survivorship gap drops from about 18% of names to 2 names.

Renames were verified in both sources: for example BK to BNY, ANTM to ELV and UTX to RTX all return full 2016-2026 history under the new ticker.
Tiingo's supported-ticker list only lists current symbols, so it needs the same rename map.

Tiingo's free tier caps at 500 unique symbols a month, so the build is a hybrid: yfinance for the roughly 612 names it covers, and Tiingo for the rest.
Returns on overlapping names should be compared across the two sources to check that their adjustments agree.

### Ticker reuse and entity chains

Tickers get reused across companies.
Examples found: `CCE` is now Carnegie Clean Energy, `VAL` before 2017 is Valspar, and `DOC` and `PARA` each have several spells in Tiingo.
Some yfinance series also stitch corporate-action chains into one history (DD across DowDuPont, HWM across Arconic).
Returns around mergers and spin-offs in these names need a sanity check for jumps.

FINRA files are keyed on the point-in-time ticker (for example, FB before 2022 and META after), so the same map is needed to join short volume to prices.

Both price sources return the newest company for a reused ticker.
yfinance "FB" is not Meta, and Tiingo "DNB" is the 2020 re-IPO, not the old Dun & Bradstreet.
Two checks catch this:

1. **Coverage:** a source is used only if it has prices for at least 90% of the ticker's days in the index.
2. **Volume agreement with FINRA:** the same stock's off-exchange and total volume move together, with a quarterly log-volume correlation of usually 0.8-0.9 and at least 0.4 even for thin names like NVR.
   Wrong-company stretches sit at 0.04-0.5.
   For example, IR in 2017-2019 (Gardner Denver data under the Ingersoll-Rand ticker) jumps to 0.89 in 2020 Q1, when the ticker actually moved.
   Ticker-quarters below 0.5 are dropped.

Unrecoverable from free sources: CCE, ESV and EQR (merged with AvalonBay in 2026; the combined ticker carries AvalonBay's history).

### Join quirks

- FINRA writes class shares as `BRK/B`; the membership list writes `BRK.B`.
- The ticker `NA` is read as a missing value by pandas unless `keep_default_na=False` is set.

### Industry

Fama-French 12 industries come from SEC SIC codes: 526 CIKs from Wikipedia's constituent table, 198 from SEC search, and 19 set by hand in `reference/industry_overrides.csv`.

### Point-in-time membership

`fja05680/sp500` is current: the last snapshot is dated 2026-08-18.
`sp500_ticker_start_end.csv` gives ticker spells, which is enough for a daily membership mask.
