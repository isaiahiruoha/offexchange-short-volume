import pandas as pd

from shortvol.prices import _unsplit


def test_unsplit_restores_raw_prices_and_volume_before_a_4_for_1_split():
    # yfinance values for AAPL around the 2020-08-31 4:1 split (split-adjusted).
    idx = pd.to_datetime(["2020-08-27", "2020-08-28", "2020-08-31"])
    adj = pd.DataFrame(
        {
            "open": [127.1425, 126.0125, 127.58],
            "high": [127.49, 126.4425, 131.0],
            "low": [123.8325, 124.5775, 126.0],
            "close": [125.01, 124.8075, 129.04],
            "volume": [155552400, 187630000, 225702700],
        },
        index=idx,
    )
    splits = pd.Series([0.0, 0.0, 4.0], index=idx)
    raw = _unsplit(adj, splits)
    # Tiingo raw closes: 500.04 and 499.23; raw volume 38,888,096 (Tiingo) vs 38,888,100.
    assert raw["close"].round(2).tolist() == [500.04, 499.23, 129.04]
    assert raw["volume"].tolist() == [38888100, 46907500, 225702700]
