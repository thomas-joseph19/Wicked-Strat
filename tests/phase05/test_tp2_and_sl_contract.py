"""TP-02 and SL distance contract via entry helpers."""

import pytest

from src.entry import (
    build_trade_setup,
    compute_sl_tp1_long,
    compute_sl_tp1_short,
    compute_tp2_long,
    compute_tp2_short,
)
from tests.phase05.conftest import SP, bar, make_lvn, ts


def test_tp2_long_two_sp_zones():
    lvn = make_lvn(99.0, 100.0)
    sps = [SP(100.5, 101.5), SP(101.75, 102.5)]
    entry = 100.2
    atr5 = 2.0
    atr20 = 4.0
    stop, tp1 = compute_sl_tp1_long(lvn, atr5, sps, entry)
    tp2 = compute_tp2_long(entry, tp1, atr20, sps, lvn, 0.25)
    assert tp1 == pytest.approx(100.5)
    assert tp2 == pytest.approx(101.75)


def test_tp2_short_two_sp_zones():
    lvn = make_lvn(100.0, 101.0)
    sps = [SP(98.5, 99.5), SP(97.0, 97.8)]
    entry = 99.8
    stop, tp1 = compute_sl_tp1_short(lvn, atr5=2.0, sp_zones=sps, entry=entry)
    tp2 = compute_tp2_short(entry, tp1, atr20=4.0, sp_zones=sps, lvn=lvn, tick_size=0.25)
    assert tp1 == pytest.approx(99.5)
    assert tp2 == pytest.approx(97.75)  # snap_tick(97.8)


def test_tp2_long_fallback_lvn_high():
    # LVN high must be strictly above tp1 for TP-02 LVN fallback branch.
    lvn = make_lvn(99.0, 101.0)
    entry = 100.1
    tp1 = 100.5
    tp2 = compute_tp2_long(entry, tp1, atr20=1.0, sp_zones=[], lvn=lvn, tick_size=0.25)
    assert tp2 == pytest.approx(101.0)


def test_sl_distance_within_bounds():
    lvn = make_lvn(100.0, 100.5)
    entry = 100.4
    atr5 = 2.0
    atr20 = 4.0
    tick = 0.25
    stop, _ = compute_sl_tp1_long(lvn, atr5, [], entry)
    risk = abs(entry - stop)
    rt = risk / tick
    assert rt >= 4 - 1e-9
    assert rt <= 1.5 * atr20 / tick + 1e-9


def test_build_trade_setup_includes_tp2():
    lvn = make_lvn(99.0, 100.0)
    sps = [SP(100.5, 101.0), SP(102.0, 103.0)]
    b = bar(ts(10, 30), 100.0, 100.6, 99.9, 100.55)
    st = build_trade_setup(
        bar_index=5,
        bar=b,
        direction="LONG",
        setup_type="THREE_STEP",
        lvn=lvn,
        structural=None,
        atr5=2.0,
        atr20=10.0,
        sp_zones=sps,
        tick_size=0.25,
    )
    assert st.tp2_price > st.target_price
