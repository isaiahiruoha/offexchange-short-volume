"""Build reference/industry.csv: FF12 industry for every ticker in the price sources."""

import pandas as pd

from shortvol import industry, prices

sources = pd.read_csv(prices.RAW_DIR / "price_sources.csv", keep_default_na=False)
sources = sources[sources.price_ticker != ""]
out = industry.build(sources)
out.to_csv(prices.ROOT / "reference" / "industry.csv", index=False)

print(out.ff12.value_counts().to_string())
print("\nno SIC:", out[out.sic.isna()].sp500_ticker.tolist())
print("\nname mismatches to review:")
print(out[~out.name_check][["sp500_ticker", "name", "sec_name", "cik_source"]].to_string())
