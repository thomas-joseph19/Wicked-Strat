"""ENTRY-03/04 + D-12–D-14 aggressive window and suppression lifecycle."""

import pandas as pd
import pytest

from src.entry import (
    AggressiveLvnState,
    evaluate_aggressive_long,
    register_aggressive_pending,
    validate_pre_entry,
)
from src.position import enter_from_setup
from tests.phase04.conftest import make_lvn, make_sp_zone, ts


def _bar_at(h: int, m: int, close: float, o: float | None = None) -> pd.Series:
    o = o if o is not None else close - 0.1
    t = ts(h, m)
    return pd.Series(
        {
            "open_nq": o,
            "high_nq": close + 0.05,
            "low_nq": close - 0.05,
            "close_nq": close,
            "open_es": o,
            "high_es": close + 0.05,
            "low_es": close - 0.05,
            "close_es": close,
            "is_synthetic_nq": False,
            "is_synthetic_es": False,
            "is_synthetic": False,
        },
        name=t,
    )


def _lvn_aggr():
    return make_lvn(100.0, 100.5)


def _sp():
    return [make_sp_zone(101.0, 102.0, True)]


def test_aggressive_long_0928_rejected():
    st = AggressiveLvnState()
    bar = _bar_at(9, 28, 101.0, o=100.85)
    assert evaluate_aggressive_long(0, bar, _lvn_aggr(), "BULLISH", 2.0, 4.0, _sp(), st) is None


def test_aggressive_long_0932_accepted():
    st = AggressiveLvnState()
    bar = _bar_at(9, 32, 101.0, o=100.85)
    setup = evaluate_aggressive_long(0, bar, _lvn_aggr(), "BULLISH", 2.0, 4.0, _sp(), st)
    assert setup is not None
    assert setup.position_size_scale == 0.5
    assert setup.setup_type == "AGGRESSIVE_LEDGE"


def test_aggressive_long_1005_rejected():
    st = AggressiveLvnState()
    bar = _bar_at(10, 5, 101.0, o=100.85)
    assert evaluate_aggressive_long(0, bar, _lvn_aggr(), "BULLISH", 2.0, 4.0, _sp(), st) is None


def test_aggressive_second_lvn_same_session_suppressed_after_enter_from_setup():
    st = AggressiveLvnState()
    lvn = _lvn_aggr()
    bar = _bar_at(9, 32, 101.0, o=100.85)
    setup = evaluate_aggressive_long(0, bar, lvn, "BULLISH", 2.0, 4.0, _sp(), st)
    assert setup is not None
    t = bar.name.time()
    ok = validate_pre_entry(
        entry_price=setup.entry_price,
        stop_price=setup.stop_price,
        target_price=setup.target_price,
        bias="BULLISH",
        atr20=4.0,
        tick_size=0.25,
        bar_time=t,
        session_setup_count=st.setups_emitted_this_session,
    )
    assert ok
    register_aggressive_pending(setup, st)
    with pytest.raises(NotImplementedError):
        enter_from_setup(setup, st)
    st.setups_emitted_this_session += 1
    setup2 = evaluate_aggressive_long(1, bar, lvn, "BULLISH", 2.0, 4.0, _sp(), st)
    assert setup2 is None


def test_aggressive_emit_accepted_without_open_does_not_add_to_suppressed_set():
    st = AggressiveLvnState()
    lvn = _lvn_aggr()
    bar = _bar_at(9, 35, 101.0, o=100.85)
    setup = evaluate_aggressive_long(0, bar, lvn, "BULLISH", 2.0, 4.0, _sp(), st)
    assert setup is not None
    t = bar.name.time()
    assert validate_pre_entry(
        entry_price=setup.entry_price,
        stop_price=setup.stop_price,
        target_price=setup.target_price,
        bias="BULLISH",
        atr20=4.0,
        tick_size=0.25,
        bar_time=t,
        session_setup_count=0,
    )
    register_aggressive_pending(setup, st)
    lid = setup.lvn_id
    assert lid not in st.aggressive_lvn_suppressed_for_session


def test_aggressive_does_not_require_structural():
    st = AggressiveLvnState()
    bar = _bar_at(9, 40, 101.0, o=100.85)
    setup = evaluate_aggressive_long(0, bar, _lvn_aggr(), "BULLISH", 2.0, 4.0, _sp(), st)
    assert setup is not None
    assert setup.ismt_or_smt_ref is None
