"""Core TP1/SL/TP2 / breakeven / conflict (D-05/D-06)."""

import pytest

from src.position import Position, PositionState
from tests.phase05.conftest import bar, simple_setup, ts


def test_long_conflict_tp1_then_breakeven_same_bar(nq_instrument, thresholds, session_budget):
    st = simple_setup(entry=100.0, stop=98.0, tp1=102.0, tp2=104.0, created_at=0)
    pos = Position(st, nq_instrument, thresholds, session_budget, 0, "2024-06-03")
    b1 = bar(ts(10, 5), 100.0, 103.0, 97.0, 101.0)
    fills = pos.update(b1, 1)
    kinds = [f.kind for f in fills]
    assert "ENTRY" in kinds
    assert "TP1_PARTIAL" in kinds
    assert "BREAKEVEN" in kinds
    assert pos.state == PositionState.CLOSED


def test_long_stop_only(nq_instrument, thresholds, session_budget):
    st = simple_setup(entry=100.0, stop=98.0, tp1=102.0, tp2=104.0, created_at=0)
    pos = Position(st, nq_instrument, thresholds, session_budget, 0, "2024-06-03")
    pos.update(bar(ts(10, 5), 100.0, 100.5, 99.5, 100.2), 1)
    b2 = bar(ts(10, 6), 100.0, 99.5, 97.0, 97.5)
    fills = pos.update(b2, 2)
    assert any(f.kind == "SL" for f in fills)
    assert pos.state == PositionState.CLOSED


def test_long_tp1_then_tp2(nq_instrument, thresholds, session_budget):
    st = simple_setup(entry=100.0, stop=98.0, tp1=102.0, tp2=104.0, created_at=0)
    pos = Position(st, nq_instrument, thresholds, session_budget, 0, "2024-06-03")
    pos.update(bar(ts(10, 5), 100.0, 102.5, 99.5, 102.0), 1)
    b3 = bar(ts(10, 7), 102.0, 105.0, 101.5, 104.5)
    fills = pos.update(b3, 3)
    assert any(f.kind == "TP2" for f in fills)
    assert pos.state == PositionState.CLOSED


def test_open_partial_tp2_before_breakeven(nq_instrument, thresholds, session_budget):
    st = simple_setup(entry=100.0, stop=98.0, tp1=102.0, tp2=104.0, created_at=0)
    pos = Position(st, nq_instrument, thresholds, session_budget, 0, "2024-06-03")
    pos.update(bar(ts(10, 5), 100.0, 102.5, 99.5, 102.0), 1)
    b = bar(ts(10, 7), 103.0, 105.0, 99.0, 104.0)
    fills = pos.update(b, 3)
    tp2_first = [f for f in fills if f.kind == "TP2"]
    assert tp2_first
    assert pos.state == PositionState.CLOSED


def test_short_conflict_tp1_then_breakeven(nq_instrument, thresholds, session_budget):
    st = simple_setup(
        entry=100.0,
        stop=102.0,
        tp1=98.0,
        tp2=96.0,
        direction="SHORT",
        created_at=0,
    )
    pos = Position(st, nq_instrument, thresholds, session_budget, 0, "2024-06-03")
    b1 = bar(ts(10, 5), 100.0, 103.0, 97.0, 99.0)
    fills = pos.update(b1, 1)
    assert "TP1_PARTIAL" in [f.kind for f in fills]
    assert "BREAKEVEN" in [f.kind for f in fills]
    assert pos.state == PositionState.CLOSED
