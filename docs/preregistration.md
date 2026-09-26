# Pre-registration

Written and committed before any signal-vs-return result was computed.
Anything run later that is not listed here is labeled exploratory.

## Question

Does the off-exchange short volume ratio predict the next tradable day's cross-sectional return, and with which sign?

- **Thesis A, informed shorting:** negative relation. Heavily shorted stocks underperform.
- **Thesis B, dealer inventory from customer buying:** the raw relation is mostly short-term reversal and fades once recent returns are controlled for. It also weakens or flips where off-exchange share is high.

## Timing and target

FINRA posts day t's file at about 17:18 ET, so the signal is traded at the next open.

- Primary target: open(t+1) to close(t+1).
- Secondary target: close(t+1) to close(t+2).

## Universe

- Point-in-time S&P 500 members on day t that have price data and a FINRA row.
- A stock-day is dropped if off-exchange volume is under 10,000 shares. Below that, the ratio is mostly noise (see `docs/data_findings.md`).
- A missing FINRA row is missing, not zero shorting.

## Sample

- Development: 2016-01-04 to 2023-12-29.
- Holdout: 2024-01-02 to 2026-08-31. It is run once, after everything else is final.

## Signals

SVR = short volume / total off-exchange volume.

1. **SVR5 (primary):** 5-day short volume divided by 5-day total volume.
2. **SVR1:** day t only.
3. **Abnormal SVR:** SVR5 minus the stock's own average over days t-65 to t-6.
4. **Shrunk SVR5:** w × SVR5 + (1 - w) × the stock's 60-day average, with w = V / (V + V0).
   V is 5-day off-exchange volume.
   V0 is the volume at which the ratio's noise equals its real variation across stocks.
   V0 is estimated once from 2016-2019 short volume data alone, never from returns.

Each signal is ranked across stocks each day, Gaussianized and then neutralized.

## Neutralization

Each day, the ranked signal is regressed across stocks on:

- day-t return
- 5-day return
- log 20-day average dollar volume
- day-t volume / 20-day average volume
- Fama-French 12 industry dummies (from SEC SIC codes)

The residual is the neutralized signal.

## Metrics

- Daily rank IC (Spearman) between signal and target: mean, Newey-West t (5 lags), and % of days positive.
- Quintile long-short: gross bps/day, turnover and break-even cost. These are reported, not pass/fail.
- IC decay at lags 1, 2, 5, 10 and 20 days.
- Raw vs neutralized IC for each signal. This is the key comparison.
- Splits: size terciles; 2016-2019, 2020-2021 and 2022-2023; off-exchange share terciles.

## Success bar

This applies to SVR5, neutralized, on the primary target:

1. Development mean IC is negative with |t| ≥ 3.
2. The same sign in at least 2 of the 3 development periods.
3. The holdout mean IC has the same sign with |t| ≥ 2.

## If the result contradicts the thesis

- **Positive sign:** Thesis B dominates. Check whether the effect concentrates in high off-exchange-share names and after up days.
- **Raw IC works but neutralized IC does not:** the finding is "it is reversal". Then test 20-day SVR against the 5-day forward return, where the paper's evidence sits.
- **Nothing works:** report it, along with the smallest IC this sample could have detected.

## Multiple testing

4 signals × 2 targets = 8 headline numbers, all reported.
