"""TP-06 / D-08: EOD bar force-flat at close; PENDING_FILL skips entry."""

from dataclasses import replace

import pytest

from src.position import ExitType, Position, PositionState
from tests.phase05.conftest import bar, make_lvn, simple_setup, ts


def test_eod_closes_open_at_close(nq_instrument, thresholds, session_budget):
    lvn = make_lvn(50.0, 55.0)
    st = replace(simple_setup(created_at=0), lvn_ref=lvn)
    pos = Position(st, nq_instrument, thresholds, session_budget, 0, "2024-06-03")
    pos.update(bar(ts(10, 5), 100.0, 100.5, 99.5, 100.2), 1)
    b_eod = bar(ts(15, 45), 100.0, 101.0, 99.8, 100.55)
    fills = pos.update(b_eod, 2)
    assert any(f.kind == "EOD" for f in fills)
    assert fills[-1].price == pytest.approx(100.55)
    assert pos.state == PositionState.CLOSED
    tr = pos.to_trade_result()
    assert tr is not None
    assert tr.exit_type == ExitType.EOD


def test_pending_fill_eod_no_entry(nq_instrument, thresholds, session_budget):
    st = simple_setup(created_at=0)
    pos = Position(st, nq_instrument, thresholds, session_budget, 0, "2024-06-03")
    fills = pos.update(bar(ts(15, 45), 100.0, 100.2, 99.9, 100.1), 1)
    assert fills == []
    assert pos.state == PositionState.CLOSED
