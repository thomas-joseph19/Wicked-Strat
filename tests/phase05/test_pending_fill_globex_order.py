"""PENDING_FILL must not treat prior Globex evening bars as session EOD before the signal bar."""

from src.position import Position, PositionState
from tests.phase05.conftest import bar, simple_setup, ts


def test_pending_fill_waits_past_eth_evening_before_rth_signal(nq_instrument, thresholds, session_budget):
    """Signal at iloc 1 (e.g. RTH); iloc 0 is prior evening (time still >= 15:45 cutoff)."""
    st = simple_setup(entry=100.0, stop=98.0, tp1=102.0, tp2=104.0, created_at=1)
    pos = Position(st, nq_instrument, thresholds, session_budget, 0, "2024-06-03")
    eth = bar(ts(18, 0), 100.0, 100.5, 99.5, 100.1)
    assert pos.update(eth, 0) == []
    assert pos.state == PositionState.PENDING_FILL
    rth = bar(ts(10, 5), 100.0, 100.5, 99.5, 100.2)
    fills = pos.update(rth, 1)
    assert any(f.kind == "ENTRY" for f in fills)
    assert pos.state in (PositionState.OPEN_FULL, PositionState.CLOSED)
