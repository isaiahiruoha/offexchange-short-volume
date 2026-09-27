# Data Findings

Verified against the sources on 2026-09-26.
Numbers come from `notebooks/01_data_quality.ipynb` unless noted.

## FINRA Reg SHO daily short volume

### One observation

AAPL on 2023-03-07, from the consolidated file:

```
Date|Symbol|ShortVolume|ShortExemptVolume|TotalVolume|Market
20230307|AAPL|9202982|102147|22405019|B,Q,N
```

`TotalVolume` is off-exchange volume only (trades reported to FINRA's trade reporting facilities), not consolidated volume.
AAPL's consolidated volume that day was 56.2M, so 40% traded off-exchange and 41% of that was marked short.
Short volume is not short interest: a market maker can short to fill a customer's buy and cover the same day.

### History and construction

The consolidated `CNMSshvol` file on `cdn.finra.org` only goes back to about 2018-08; earlier dates return 403.
The per-facility files go back to 2009-11:

| Prefix | Facility | Market code | Available from |
|---|---|---|---|
| `FNSQshvol` | Nasdaq TRF Carteret | Q | 2009-11 |
| `FNYXshvol` | NYSE TRF | N | 2009-11 |
| `FNQCshvol` | Nasdaq TRF Chicago | B | 2018-08-01 |
| `FNRAshvol` | ADF | D | files exist, no S&P 500 volume |
| `FORFshvol` | ORF (OTC, non-NMS) | - | not part of CNMS |

The panel sums Q + N + B per symbol per day, which reproduces CNMS exactly (all 9,845 symbols checked on 2023-03-07).
This gives one construction across the whole sample.
Nasdaq Chicago (B) is a small break from 2018-08 (under 1% of volume).

Result: 2,680 trading days (2016-01-04 to 2026-08-31), 24.3M rows, 25,693 symbols.

### Publication time

The CDN `Last-Modified` header is about 17:18 ET on the trade date, after the close and before the next open.
The tradable target is therefore open(t+1) to close(t+1); close(t) to close(t+1) would be look-ahead.
Files before about 2021 carry 2021 upload stamps, so their original timing cannot be verified and silent restatement cannot be ruled out.

### Quality issues

- **Thin days are noise.** Below 10,000 off-exchange shares, 31% (under 1k) to 3% (5-10k) of days read as 95%+ short. Hence the 10k floor, which removes 0.12% of S&P 500 stock-days.
- **Missing rows** (0.52% of S&P 500 stock-days) mean no off-exchange trading was reported, not zero shorting. Coverage is weakest in small and mid names (0.6%) and best in large (0.3%).
- **Level shifts.** The market-wide ratio moved from about 0.44 (2017-2021) to about 0.50 (2023-2026). Ranking across stocks each day removes this.
- **Facility mix changed.** NYSE TRF's share of volume fell from 15-21% to about 4% in 2024. Cause not established.
- **Parsing.** The ticker `NA` becomes a missing value in pandas unless `keep_default_na=False`; FINRA writes class shares as `BRK/B`, not `BRK.B`.

### What the ratio looks like (S&P 500)

- Mean 0.47, standard deviation 0.15.
- 87% of the variation is within a stock over time; 13% is persistent differences between stocks.
- Day-to-day autocorrelation 0.61.
- Smaller S&P 500 names have higher ratios (0.50 vs 0.44 for the largest), the opposite of the full-market pattern in Wang, Yan and Zheng (2020).
- Off-exchange share of volume rose from a median of 0.23 (2018) to 0.36 (2025-26).

## Prices and universe

### Universe

Point-in-time S&P 500 membership from `fja05680/sp500` (ticker spells, last update 2026-08-18): 745 tickers over 2016-2026, about 500 a day.

### Survivorship and ticker reuse

yfinance returns nothing for delisted tickers: 133 of the 745 names had no data.
They are recovered through:

- **Tiingo's free tier** for delisted names (50 requests/hour).
- **A rename map** (`reference/ticker_map.csv`) for companies that changed ticker, e.g. FB to META, BBT to TFC.
- **OTC tickers** for bankruptcies: SIVB to SIVBQ, FRC to FRCB, BBBY to BBBYQ.

Both sources return the *newest* company for a reused ticker (yfinance "FB" is not Meta; Tiingo "DNB" is the 2020 re-IPO).
Two checks catch this:

1. **Coverage:** a source is used only if it has prices for at least 90% of the ticker's days in the index.
2. **Volume agreement with FINRA:** a stock's off-exchange and total volume move together (quarterly log-volume correlation 0.86 median).
   Two or more consecutive quarters below 0.5 mean a different company, and those quarters are dropped.
   IR in 2017-2019 (Gardner Denver data under Ingersoll-Rand's ticker) sits at 0.04-0.5 and jumps to 0.89 when the ticker actually moved in 2020.

yfinance prices and volume are split-adjusted; they are converted back to as-traded values so volume is comparable with FINRA's raw share counts.

Final panel: 1,335,547 stock-days, 98.8% of all member-days.
Unrecoverable from free sources: CCE, ESV and EQR.

### Industry

Fama-French 12 industries from SEC SIC codes: 526 CIKs from Wikipedia's constituent table, 198 from SEC search, 19 set by hand (`reference/industry_overrides.csv`).
