"""Build reference/industry.csv: FF12 industry for every ticker in the price sources."""

import pandas as pd

from shortvol import industry, prices

sources = pd.read_csv(prices.RAW_DIR / "price_sources.csv", keep_default_na=False)
sources = sources[sources.price_ticker != ""]
out = industry.build(sources)

# Names SEC search could not resolve (or resolved to the wrong company), set by hand.
manual = pd.read_csv(prices.ROOT / "reference" / "industry_overrides.csv").set_index("sp500_ticker")
hit = out.sp500_ticker.isin(manual.index)
out.loc[hit, "ff12"] = out.loc[hit, "sp500_ticker"].map(manual.ff12)
out.loc[hit, "cik_source"] = "manual"
out.to_csv(prices.ROOT / "reference" / "industry.csv", index=False)

print(out.ff12.value_counts().to_string())
print("\nby source:", out.cik_source.value_counts().to_dict())
