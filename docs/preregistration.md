# Pre-registration (DRAFT - not yet frozen)

This file fixes the tests before any signal-vs-return result is computed.
It is frozen by a git commit titled "Freeze pre-registration".
Anything run after that commit and not listed here is reported as exploratory.

Items marked **[DECIDE]** need sign-off before freezing.

## Question

Does the off-exchange short volume ratio predict the next tradable day's cross-sectional return, and with which sign?

- Thesis A (informed shorting) predicts a **negative** relation: heavily shorted stocks underperform.
- Thesis B (dealer inventory from customer buying) predicts the raw relation is mostly short-term reversal, so it should shrink toward zero once day-t and 5-day returns are controlled for.
  It also predicts the relation weakens or flips where off-exchange share is high.

## Data and timing

- Short volume: FINRA per-facility files summed to the CNMS definition (Q + N + B + D).
- FINRA posts at about 17:18 ET on day t, so the signal known at day t is traded at the open of t+1.
- Primary target: open(t+1) to close(t+1) return, raw prices.
- Secondary target: close(t+1) to close(t+2), adjusted prices.
- Both targets are ranked cross-sectionally each day, so market direction drops out.

## Universe

- Point-in-time S&P 500 members on day t (fja05680 spells), with price data and a FINRA row.
- Exclude a stock-day if off-exchange total volume is below 10,000 shares. **[DECIDE]** the floor.
- A missing FINRA row is treated as missing, not as zero short volume (a deliberate departure from Wang, Yan & Zheng 2020).

## Sample split

- Development: 2016-01-04 to 2023-12-29.
- Holdout: 2024-01-02 to 2026-08-31, untouched until the development results and all choices are final. It is run exactly once.

## Signal variants (at most 6, all reported)

Let SVR_t = short_volume_t / total_volume_t.

1. **SVR5**: sum of short volume over t-4..t divided by sum of total volume over the same days (the paper's construction, volume-weighted). **Primary.**
2. **SVR1**: day-t SVR.
3. **Abnormal SVR**: SVR5 minus the stock's own mean SVR over t-65..t-6. The paper finds this does not predict in 2010-2015.
4. **Shrunk SVR5**: w * SVR5 + (1 - w) * the stock's 60-day mean, with w = n / (n + k), n = log off-exchange volume, k = 10. **[DECIDE]** k, fixed before looking.

Each variant is ranked cross-sectionally, Gaussianized, winsorized at 1/99 and then neutralized.

## Neutralization

Cross-sectional OLS each day of the ranked signal on:

- day-t return (close t-1 to close t)
- 5-day return (close t-5 to close t)
- log 20-day average dollar volume (size and liquidity proxy; free market cap is not available)
- abnormal volume: day-t volume over 20-day average volume
- industry dummies **[DECIDE]** source: SEC SIC codes mapped to Fama-French 12, or skip industry

The residual is the neutralized signal.

## Metrics

- Daily Spearman rank IC between signal and target.
- Mean IC, Newey-West t-stat (5 lags), IC information ratio, % of days with IC > 0.
- Quintile long-short: gross bps/day, daily turnover and the break-even one-way cost.
- IC decay: signal at t vs target at t+1, t+2, t+5, t+10, t+20.
- **Key comparison:** raw IC vs neutralized IC for each variant.

## Splits

- Size terciles (by 20-day dollar volume).
- Periods: 2016-2019, 2020-2021, 2022-2023 (development) and 2024-2026 (holdout).
- Off-exchange share terciles, where off-exchange share = FINRA total volume / consolidated volume.

## Success bar (for the primary variant SVR5, neutralized, primary target)

The signal "works" only if all of these hold:

1. Development mean IC has the Thesis A sign (negative) with |Newey-West t| >= 3.
2. Same sign in at least 2 of the 3 development subperiods.
3. Holdout mean IC has the same sign with |t| >= 2.
4. Quintile long-short break-even cost above 2 bps one-way.

**[DECIDE]** these thresholds.

## If the results contradict the thesis

- **Positive sign:** Thesis B dominates. Check whether the effect concentrates in high off-exchange-share names and after up days (day-t return > 0).
- **Raw IC significant, neutralized IC near zero:** the finding is "it is reversal". Report the gap as the result.
  Then test the slow version (20-day SVR against 5-day forward return), where the paper's evidence suggests the information lives.
- **Nothing anywhere:** report it, with the power calculation (what IC size the sample could detect).

## Multiple testing

Four variants times two targets gives eight headline numbers.
All of them are reported, not only the best.
Anything else is labeled exploratory.
