# Off-Exchange Short Volume as a Next-Day Signal

Predicting which S&P 500 stocks outperform tomorrow from one public data source: FINRA's daily off-exchange short sale volume.

## Result

The **1-day short volume ratio** (short volume / off-exchange volume on day t) predicts the next session's return with a negative sign: stocks with unusually heavy off-exchange shorting today underperform tomorrow.

- It holds after removing day-t and 5-day returns (reversal), size, volume and industry.
- It met every pre-registered criterion, including an untouched 2024-2026 holdout, and survives a correction for the eight signal-target combinations tested.
- The effect lasts one session, is strongest in the most heavily traded names (by 20-day dollar volume), after down days and where more volume trades off-exchange, and is not explained by standard factors (alpha 2.0 bps/day, t 3.7).
- It is a micro-signal: about 1.8 bps/day gross, break-even cost about 1 bp. It is useful as one input among many, not on its own.

The pre-registered primary, a 5-day average ratio, did not predict next-day returns.

## Notebooks

| Notebook | What it does |
|---|---|
| `01_data_quality` | Coverage, one observation, the 10k floor, the ratio's distribution, price-source validation |
| `02_signals` | Builds the four pre-registered signals and their same-day relationships to the controls |
| `03_evaluation` | Pre-registered tests on 2016-2023 |
| `04_holdout` | The single run on 2024-2026 |
| `05_one_day_signal` | The 1-day signal in depth: success bar, stability, decay, where it works, backtest, factor check |

## Layout

```
src/shortvol/   finra, prices, industry, panel, features, evaluate, factors
scripts/        download and build steps
reference/      ticker rename map and industry codes (hand-checked, committed)
docs/           data findings and the pre-registration
data/           raw, interim and processed data (gitignored, rebuilt by the scripts)
```

## Setup

The project folder ends in `.nosync` so iCloud Desktop sync leaves it alone; `offexchange-short-volume` is a link to it.

```bash
python3 -m venv .venv.nosync && ln -s .venv.nosync .venv
.venv/bin/pip install -e ".[dev]"
cp .env.example .env    # add a free TIINGO_API_KEY
```

Build the data in order, then open the notebooks with `.venv/bin/jupyter lab`:

```bash
.venv/bin/python scripts/download_finra.py     # ~15 min
.venv/bin/python scripts/download_prices.py    # yfinance, then Tiingo at 48 requests/hour
.venv/bin/python scripts/build_industry.py
.venv/bin/python scripts/build_panel.py
```

## Documents

- `docs/data_findings.md`: verified facts about the data and its quirks
- `docs/preregistration.md`: the evaluation plan, frozen before any results
