from pathlib import Path

from shortvol import finra

SAMPLE = """Date|Symbol|ShortVolume|ShortExemptVolume|TotalVolume|Market
20230307|AAPL|5029587|91298|12378308|Q
20230307|AAMpA|10|0|20|Q
20230307|NA|121|26|30353|Q
2
"""


def test_read_file_drops_trailer_and_keeps_suffixed_symbols(tmp_path: Path):
    p = tmp_path / "FNSQshvol20230307.txt"
    p.write_text(SAMPLE)
    df = finra.read_file(p)
    assert list(df["Symbol"]) == ["AAPL", "AAMpA", "NA"]
    assert df["ShortVolume"].astype(int).tolist() == [5029587, 10, 121]


def test_trading_days_skips_weekends_and_holidays():
    days = finra.trading_days("2023-12-22", "2023-12-27")
    assert [d.strftime("%Y-%m-%d") for d in days] == ["2023-12-22", "2023-12-26", "2023-12-27"]
