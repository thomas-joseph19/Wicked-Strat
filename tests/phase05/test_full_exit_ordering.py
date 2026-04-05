"""Per-bar ordering: EOD / hard stop before TP path; D-05/D-06 regression."""

from dataclasses import replace

import pytest

from src.position import Position, PositionState
from tests.phase05.conftest import bar, make_lvn, simple_setup, ts


def test_eod_supersedes_tp1(nq_instrument, thresholds, session_budget):
    st = replace(simple_setup(created_at=0), lvn_ref=make_lvn(50.0, 55.0))
    pos = Position(st, nq_instrument, thresholds, session_budget, 0, "2024-06-03")
    pos.update(bar(ts(10, 5), 100.0, 100.5, 99.5, 100.2), 1)
    b_eod = bar(ts(15, 45), 100.0, 104.0, 99.5, 100.25)
    fills = pos.update(b_eod, 2)
    assert [f.kind for f in fills] == ["EOD"]
    assert fills[0].price == pytest.approx(100.25)


def test_hard_stop_supersedes_tp2_open_partial(nq_instrument, thresholds, session_budget):
    lvn = make_lvn(104.0, 106.0)
    st = replace(
        simple_setup(entry=100.0, stop=98.0, tp1=102.0, tp2=105.0, created_at=0),
        lvn_ref=lvn,
    )
    pos = Position(st, nq_instrument, thresholds, session_budget, 0, "2024-06-03")
    pos.update(bar(ts(10, 5), 99.0, 102.5, 98.5, 102.0), 1)
    b_hs = bar(ts(10, 10), 104.5, 106.0, 104.0, 105.2)
    fills = pos.update(b_hs, 2)
    assert "TP2" not in [f.kind for f in fills]
    assert any(f.kind == "HARD_STOP_LVN" for f in fills)
    assert fills[-1].kind == "HARD_STOP_LVN"
    assert pos.state == PositionState.CLOSED


def test_d05_d06_conflict_tp1_then_breakeven_still_holds(nq_instrument, thresholds, session_budget):
    st = replace(simple_setup(created_at=0), lvn_ref=make_lvn(50.0, 55.0))
    pos = Position(st, nq_instrument, thresholds, session_budget, 0, "2024-06-03")
    b1 = bar(ts(10, 5), 100.0, 103.0, 97.0, 101.0)
    fills = pos.update(b1, 1)
    assert "TP1_PARTIAL" in [f.kind for f in fills]
    assert "BREAKEVEN" in [f.kind for f in fills]
    assert pos.state == PositionState.CLOSED
