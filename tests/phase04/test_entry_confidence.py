"""Confidence-weighted entry: partial confluence → score vs threshold."""

from __future__ import annotations

from dataclasses import replace

import pandas as pd

from src.config import StrategyThresholds
from src.entry_confidence import (
    entry_confidence_long,
    evaluate_confidence_long,
    evaluate_confidence_short,
)
from src.ismt import IsmtSignal
from tests.phase04.conftest import TICK_SIZE, make_bar_row, make_lvn, make_sp_zone, make_swing, ts


def _prior_above_lvn(i_base: int, lvn_high: float) -> list[pd.Series]:
    out: list[pd.Series] = []
    for k, c in enumerate([lvn_high + 1, lvn_high + 2, lvn_high + 3]):
        out.append(
            make_bar_row(
                i_base + k,
                o=c,
                h=c + 0.5,
                l=c - 0.5,
                c=c,
                timestamp=ts(9, 35 + k),
            )
        )
    return out


def test_entry_confidence_long_high_score():
    lvn = make_lvn(5299.5, 5300.5)
    prior = _prior_above_lvn(0, lvn.high)
    t_sig = ts(9, 45)
    bar = make_bar_row(
        10,
        o=float(prior[-1]["close_nq"]),
        h=5310.0,
        l=float(lvn.high) - 0.5,
        c=5305.0,
        timestamp=t_sig,
    )
    sw = make_swing(0, 5, 5300.0, "HIGH")
    ismt = IsmtSignal(
        direction="LONG",
        confirmed_at=10,
        sweep_size=1.0,
        entry_zone=5300.0,
        source_swings=(sw, sw),
    )
    sp = [make_sp_zone(5306.0, 5310.0, respected_overnight=True)]
    th = StrategyThresholds()
    s = entry_confidence_long(
        10,
        bar,
        prior,
        lvn,
        "BULLISH",
        sp,
        [ismt],
        [],
        TICK_SIZE,
        th,
    )
    assert s >= float(th.entry_confidence_threshold)


def test_evaluate_confidence_respects_threshold():
    lvn = make_lvn(5299.5, 5300.5)
    prior = _prior_above_lvn(0, lvn.high)
    bar = make_bar_row(
        10,
        o=float(prior[-1]["close_nq"]),
        h=5310.0,
        l=float(lvn.high) - 0.5,
        c=5305.0,
        timestamp=ts(9, 45),
    )
    sw = make_swing(0, 5, 5300.0, "HIGH")
    ismt = IsmtSignal(
        direction="LONG",
        confirmed_at=10,
        sweep_size=1.0,
        entry_zone=5300.0,
        source_swings=(sw, sw),
    )
    sp = [make_sp_zone(5306.0, 5310.0, respected_overnight=True)]
    th_hi = replace(StrategyThresholds(), entry_confidence_threshold=0.99)
    assert (
        evaluate_confidence_long(
            10,
            bar,
            prior,
            lvn,
            "BULLISH",
            sp,
            [ismt],
            [],
            2.0,
            4.0,
            TICK_SIZE,
            th_hi,
        )
        is None
    )
    th_lo = replace(StrategyThresholds(), entry_confidence_threshold=0.30)
    setup = evaluate_confidence_long(
        10,
        bar,
        prior,
        lvn,
        "BULLISH",
        sp,
        [ismt],
        [],
        2.0,
        4.0,
        TICK_SIZE,
        th_lo,
    )
    assert setup is not None
    assert setup.setup_type == "CONFIDENCE_SCORE"
    assert setup.direction == "LONG"


def test_evaluate_confidence_short_neutral_bias():
    lvn = make_lvn(5299.5, 5300.5)
    prior = []
    for k, c in enumerate([lvn.low - 3, lvn.low - 2, lvn.low - 1]):
        prior.append(
            make_bar_row(
                k,
                o=c,
                h=c + 0.5,
                l=c - 0.5,
                c=c,
                timestamp=ts(9, 35 + k),
            )
        )
    bar = make_bar_row(
        10,
        o=float(prior[-1]["close_nq"]),
        h=float(lvn.low) + 0.5,
        l=float(lvn.low) - 2.0,
        c=float(lvn.low) - 2.5,
        timestamp=ts(9, 45),
    )
    sw = make_swing(0, 5, lvn.low, "LOW")
    ismt = IsmtSignal(
        direction="SHORT",
        confirmed_at=10,
        sweep_size=1.0,
        entry_zone=float(lvn.low),
        source_swings=(sw, sw),
    )
    sp = [make_sp_zone(5288.0, 5292.0, respected_overnight=True)]
    th_lo = replace(StrategyThresholds(), entry_confidence_threshold=0.30)
    setup = evaluate_confidence_short(
        10,
        bar,
        prior,
        lvn,
        "NEUTRAL",
        sp,
        [ismt],
        [],
        2.0,
        4.0,
        TICK_SIZE,
        th_lo,
    )
    assert setup is not None
    assert setup.setup_type == "CONFIDENCE_SCORE"


def test_explain_pre_entry_allows_neutral_when_flag():
    from datetime import time as dtime

    from src.entry import explain_pre_entry_failure

    r = explain_pre_entry_failure(
        entry_price=5300.0,
        stop_price=5290.0,
        target_price=5320.0,
        bias="NEUTRAL",
        atr20=10.0,
        tick_size=0.25,
        bar_time=dtime(10, 0),
        session_setup_count=0,
        allow_neutral_bias=True,
    )
    assert r is None
