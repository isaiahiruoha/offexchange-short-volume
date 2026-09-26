# Off-Exchange Short Volume as a Next-Day Signal

Next-day cross-sectional equity return prediction from one public data source.

**Question:** Does FINRA's off-exchange short volume ratio measure informed short-selling (bearish) or dealer inventory from customer buying (bullish, then reversal)?
Does either survive at a one-day horizon after controlling for short-term reversal?

## Layout

```
src/shortvol/     library code (data loaders, features, evaluation)
scripts/          entry points that pull data and run the pipeline
notebooks/        exploration and figures
tests/            unit tests (timing alignment, symbol mapping, feature math)
data/             raw / interim / processed, gitignored, rebuilt from scripts
reports/figures/  charts used in slides
docs/             research brief, pre-registration, data findings
slides/           presentation drafts
```

## Setup

```bash
python3 -m venv .venv.nosync          # .nosync keeps iCloud from hiding files Python needs
ln -s .venv.nosync .venv
.venv/bin/pip install -e ".[dev]" lxml
cp .env.example .env                  # add TIINGO_API_KEY
```

Pipeline order: `download_finra.py`, `download_prices.py`, `build_industry.py`.

## Key documents

- `docs/data_findings.md` - verified facts about the data sources
- `docs/preregistration.md` - evaluation criteria, frozen before looking at results
