import numpy as np
import pandas as pd

from shortvol import evaluate


def synthetic(n_days=120, n_stocks=200, seed=0):
    """Target = -0.1 * signal + noise; signal is partly a control (ret1)."""
    rng = np.random.default_rng(seed)
    dates = np.repeat(pd.bdate_range("2020-01-01", periods=n_days), n_stocks)
    ret1 = rng.normal(size=len(dates))
    own = rng.normal(size=len(dates))
    return pd.DataFrame({
        "date": dates,
        "ticker": np.tile([f"S{i}" for i in range(n_stocks)], n_days),
        "day": np.repeat(np.arange(n_days), n_stocks),
        "ret1": ret1,
        "own": own,
        "signal": own + 2 * ret1,
        "target": -0.1 * own + rng.normal(size=len(dates)),
        "ff12": rng.choice(["A", "B", "C"], size=len(dates)),
    })


def test_daily_ic_recovers_planted_negative_relation():
    df = synthetic()
    s = evaluate.summarize_ic(evaluate.daily_ic(df, "own", "target"))
    assert -0.15 < s["mean_ic"] < -0.05
    assert s["nw_t"] < -5


def test_neutralize_removes_the_control():
    df = synthetic()
    df["neutral"] = evaluate.neutralize(df, "signal", ["ret1"])
    corr_raw = df.groupby("date")[["signal", "ret1"]].corr().xs("ret1", level=1)["signal"].mean()
    corr_neutral = df.groupby("date")[["neutral", "ret1"]].corr().xs("ret1", level=1)["neutral"].mean()
    assert corr_raw > 0.8
    assert abs(corr_neutral) < 0.05


def test_quintile_spread_sign_and_breakeven():
    df = synthetic()
    q = evaluate.quintile_spread(df, "own", "target")
    assert q["spread_bps"] < 0
    assert 1.0 < q["turnover"] <= 4.0  # fresh random signal each day: most names turn over
    assert q["breakeven_bps"] > 0
