"""ENTRY-01/02 — 3-Step model pillars."""

import pandas as pd

from src.entry import evaluate_three_step_long, evaluate_three_step_short
from src.ismt import IsmtSignal
from tests.phase04.conftest import make_lvn, make_sp_zone, make_swing, ts


def _bars_long_setup():
    """Prior 3 closes > 100; touch; then bullish close above LVN.high."""
    rows = []
    for k in range(9):
        ti = ts(10, k)
        rows.append(
            pd.Series(
                {
                    "open_nq": 100.2,
                    "high_nq": 100.3,
                    "low_nq": 100.15,
                    "close_nq": 100.25,
                    "open_es": 100.2,
                    "high_es": 100.3,
                    "low_es": 100.15,
                    "close_es": 100.25,
                    "is_synthetic_nq": False,
                    "is_synthetic_es": False,
                    "is_synthetic": False,
                },
                name=ti,
            )
        )
    ti = ts(10, 9)
    bar = pd.Series(
        {
            "open_nq": 100.35,
            "high_nq": 100.55,
            "low_nq": 99.95,
            "close_nq": 100.45,
            "open_es": 100.35,
            "high_es": 100.55,
            "low_es": 99.95,
            "close_es": 100.45,
            "is_synthetic_nq": False,
            "is_synthetic_es": False,
            "is_synthetic": False,
        },
        name=ti,
    )
    rows.append(bar)
    return rows, bar


def _struct_long(i: int) -> IsmtSignal:
    s1 = make_swing(0, i - 2, 99.0, "LOW")
    s2 = make_swing(0, i - 1, 98.5, "LOW")
    return IsmtSignal(
        direction="LONG",
        confirmed_at=i,
        sweep_size=0.5,
        entry_zone=99.0,
        source_swings=(s1, s2),
    )


def test_three_step_long_requires_all_pillars():
    rows, bar = _bars_long_setup()
    i = 9
    prior = rows[:i]
    lvn = make_lvn(99.0, 100.0)
    sp_ok = [make_sp_zone(100.5, 101.5, True)]
    struct = [_struct_long(i)]

    assert evaluate_three_step_long(i, bar, prior, lvn, sp_ok, struct, [], 2.0, 4.0) is not None
    assert evaluate_three_step_long(i, bar, prior, lvn, [], struct, [], 2.0, 4.0) is None
    assert evaluate_three_step_long(i, bar, prior, lvn, sp_ok, [], [], 2.0, 4.0) is None

    bad_prior = list(prior)
    bad_prior[-1] = prior[-1].copy()
    bad_prior[-1]["close_nq"] = 99.5
    assert evaluate_three_step_long(i, bar, bad_prior, lvn, sp_ok, struct, [], 2.0, 4.0) is None

    bad_lvn = make_lvn(99.0, 100.0, valid=False)
    assert evaluate_three_step_long(i, bar, prior, bad_lvn, sp_ok, struct, [], 2.0, 4.0) is None


def test_three_step_short_mirror():
    rows = []
    for k in range(9):
        ti = ts(11, k)
        rows.append(
            pd.Series(
                {
                    "open_nq": 99.7,
                    "high_nq": 99.85,
                    "low_nq": 99.65,
                    "close_nq": 99.75,
                    "open_es": 99.7,
                    "high_es": 99.85,
                    "low_es": 99.65,
                    "close_es": 99.75,
                    "is_synthetic_nq": False,
                    "is_synthetic_es": False,
                    "is_synthetic": False,
                },
                name=ti,
            )
        )
    ti = ts(11, 9)
    bar = pd.Series(
        {
            "open_nq": 99.65,
            "high_nq": 100.05,
            "low_nq": 99.45,
            "close_nq": 99.55,
            "open_es": 99.65,
            "high_es": 100.05,
            "low_es": 99.45,
            "close_es": 99.55,
            "is_synthetic_nq": False,
            "is_synthetic_es": False,
            "is_synthetic": False,
        },
        name=ti,
    )
    rows.append(bar)
    i = 9
    prior = rows[:i]
    lvn = make_lvn(100.0, 101.0)
    sp_ok = [make_sp_zone(98.0, 99.0, True)]
    s1 = make_swing(0, i - 2, 102.0, "HIGH")
    s2 = make_swing(0, i - 1, 102.5, "HIGH")
    struct = [
        IsmtSignal(
            direction="SHORT",
            confirmed_at=i,
            sweep_size=0.5,
            entry_zone=102.0,
            source_swings=(s1, s2),
        )
    ]
    assert evaluate_three_step_short(i, bar, prior, lvn, sp_ok, struct, [], 2.0, 4.0) is not None
