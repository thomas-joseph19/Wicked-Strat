"""TP-05 / D-07: body fully inside trade LVN → HARD_STOP_LVN at close."""

from dataclasses import replace

import pytest

from src.position import ExitType, Position, PositionState, body_inside_lvn
from tests.phase05.conftest import bar, make_lvn, simple_setup, ts


def test_body_inside_lvn_true():
    lvn = make_lvn(100.0, 102.0)
    b = bar(ts(10, 30), 100.5, 101.2, 100.4, 100.9)
    assert body_inside_lvn(b, lvn) is True


def test_wick_through_zone_body_outside():
    lvn = make_lvn(100.0, 101.0)
    b = bar(ts(10, 30), 102.0, 102.5, 99.5, 102.2)
    assert body_inside_lvn(b, lvn) is False


def test_body_straddles_lvn_edge_not_subset():
    lvn = make_lvn(100.0, 101.0)
    b = bar(ts(10, 30), 99.5, 100.2, 99.4, 99.8)
    assert body_inside_lvn(b, lvn) is False


def test_hard_stop_long_closes_at_close(nq_instrument, thresholds, session_budget):
    lvn = make_lvn(100.0, 102.0)
    st = simple_setup(entry=100.0, stop=98.0, tp1=102.0, tp2=104.0, created_at=0)
    st = replace(st, lvn_ref=lvn, lvn_id="hs")
    pos = Position(st, nq_instrument, thresholds, session_budget, 0, "2024-06-03")
    pos.update(bar(ts(10, 5), 103.0, 104.0, 102.5, 103.5), 1)
    b2 = bar(ts(10, 10), 100.5, 101.0, 100.4, 100.85)
    fills = pos.update(b2, 2)
    assert any(f.kind == "HARD_STOP_LVN" for f in fills)
    assert fills[-1].price == pytest.approx(100.85)
    assert pos.state == PositionState.CLOSED
    tr = pos.to_trade_result()
    assert tr is not None
    assert tr.exit_type == ExitType.HARD_STOP


def test_hard_stop_no_further_fills_same_bar(nq_instrument, thresholds, session_budget):
    lvn = make_lvn(99.0, 101.0)
    st = simple_setup(entry=100.0, stop=98.0, tp1=102.0, tp2=104.0, created_at=0)
    st = replace(st, lvn_ref=lvn)
    pos = Position(st, nq_instrument, thresholds, session_budget, 0, "2024-06-03")
    pos.update(bar(ts(10, 5), 102.0, 102.5, 101.5, 102.2), 1)
    b2 = bar(ts(10, 10), 99.5, 100.5, 99.4, 100.0)
    fills = pos.update(b2, 2)
    assert [f.kind for f in fills] == ["HARD_STOP_LVN"]
