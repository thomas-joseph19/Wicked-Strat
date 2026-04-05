"""Phase 5.1: last bar before 15:45 — open position still yields TradeResult after flush."""

from dataclasses import replace

import pandas as pd

from src.backtest import run_session_backtest
from src.config import make_run_paths
from src.position import ExitType, Position, PositionState
from src.volume_profile import build_volume_profile
from tests.phase05.conftest import bar, make_lvn, simple_setup, ts


def test_force_end_of_session_flat_closes_open_position(nq_instrument, thresholds, session_budget):
    lvn = make_lvn(50.0, 55.0)
    st = replace(simple_setup(created_at=0), lvn_ref=lvn)
    pos = Position(st, nq_instrument, thresholds, session_budget, 0, "2024-06-03")
    pos.update(bar(ts(10, 5), 100.0, 100.5, 99.5, 100.2), 1)
    assert pos.state == PositionState.OPEN_FULL
    last = bar(ts(10, 30), 100.0, 100.4, 99.9, 100.15)
    pos.force_end_of_session_flat(last, 2)
    assert pos.state == PositionState.CLOSED
    tr = pos.to_trade_result()
    assert tr is not None
    assert tr.exit_type == ExitType.EOD


def test_run_session_backtest_flushes_when_last_bar_not_eod(nq_instrument, thresholds, tmp_path):
    """No bar >= 15:45; position would stay open without Phase 5.1 flush."""
    paths = make_run_paths(tmp_path, run_ts="20260101_120000")
    lvn = make_lvn(50.0, 55.0)
    st = replace(
        simple_setup(entry=100.0, stop=99.0, tp1=100.5, tp2=101.0, created_at=0),
        lvn_ref=lvn,
    )
    raw = [
        bar(ts(10, 0), 100.0, 100.2, 99.9, 100.05),
        bar(ts(10, 1), 100.0, 100.2, 99.9, 100.05),
    ]
    rows = []
    for s in raw:
        s2 = s.copy()
        s2["volume_nq"] = 1000.0
        rows.append(s2)
    df = pd.DataFrame(rows)
    df.index = [r.name for r in rows]
    vp = build_volume_profile("2024-06-03", df, nq_instrument.tick_size)
    out = run_session_backtest(
        bars_df=df,
        setups=[st],
        instrument=nq_instrument,
        thresholds=thresholds,
        paths=paths,
        session_date="2024-06-03",
        volume_profile=vp,
        writer=None,
    )
    assert len(out) == 1
    assert out[0].exit_type == ExitType.EOD
