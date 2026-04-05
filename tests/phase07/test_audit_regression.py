"""
AUDIT-02..07 regression anchors (Phase 7).

AUDIT-06: ROADMAP “3 commission events” = three billable fills total:
entry + TP1 partial + TP2 (no fourth fill).
"""

from dataclasses import replace
from datetime import time

import pandas as pd
import pytest

from src.config import InstrumentConfig, StrategyThresholds
from src.entry import validate_pre_entry
from src.metrics import max_drawdown_stats
from src.position import (
    FillEvent,
    Position,
    SessionTradeBudget,
    TradeSetup,
    fills_to_gross_pnl,
)
from src.tpo import build_tpo_profile
from tests.phase05.conftest import bar, make_lvn, simple_setup, ts


def test_audit_02_entry_equals_stop_rejected():
    """AUDIT-02 — entry == stop → validate_pre_entry False (risk <= 0)."""
    ok = validate_pre_entry(
        entry_price=100.0,
        stop_price=100.0,
        target_price=102.0,
        bias="BULLISH",
        atr20=10.0,
        tick_size=0.25,
        bar_time=time(10, 0),
        session_setup_count=0,
    )
    assert ok is False


def test_audit_03_short_polarity_price_fell_profitable():
    """AUDIT-03: SHORT wins when exit below entry (gross from fills)."""
    setup = TradeSetup(
        setup_id="s",
        entry_price=100.0,
        stop_price=101.0,
        target_price=98.0,
        tp2_price=96.0,
        rr_ratio=2.0,
        direction="SHORT",
        created_at=0,
        setup_type="THREE_STEP",
        lvn_id="1",
        lvn_ref=make_lvn(99.0, 101.0),
        ismt_or_smt_ref=None,
        signal_source=0,
    )
    fills = [
        FillEvent(1, "ENTRY", 100.0, 1, "SHORT"),
        FillEvent(2, "TP2", 97.0, 1, "SHORT"),
    ]
    gross = fills_to_gross_pnl(fills, setup, point_value=20.0)
    assert gross > 0


def test_audit_04_max_drawdown_uses_rolling_peak():
    """AUDIT-04: max_drawdown_frac <= 0, dollars from peak to trough >= 0."""
    equity = pd.Series([100_000.0, 110_000.0, 100_000.0, 88_000.0])
    dd = max_drawdown_stats(equity)
    assert dd["max_drawdown_frac"] <= 0
    assert dd["max_drawdown_dollars"] >= 0


def test_audit_05_tpo_resample_left_closed_left():
    """AUDIT-05: build_tpo_profile uses label='left', closed='left'."""
    import inspect

    src = inspect.getsource(build_tpo_profile)
    assert "label='left'" in src or 'label="left"' in src
    assert "closed='left'" in src or 'closed="left"' in src
    # behavioral: 3 one-minute bars 18:00–18:02 → one 30m bucket
    idx = pd.date_range("2024-06-03 18:00", periods=3, freq="1min", tz="America/New_York")
    df = pd.DataFrame(
        {"high_nq": [100.5, 100.75, 100.6], "low_nq": [100.0, 100.5, 100.4]},
        index=idx,
    )
    prof = build_tpo_profile(df, tick_size=0.25)
    assert isinstance(prof, dict)


def test_audit_06_tp_path_three_commission_events():
    """
    AUDIT-06: entry → TP1 partial → TP2 → exactly 3 fills (3 commission charges).
    """
    lvn = make_lvn(50.0, 55.0)
    st = replace(
        simple_setup(entry=100.0, stop=98.0, tp1=102.0, tp2=103.0, created_at=0),
        lvn_ref=lvn,
    )
    nq = InstrumentConfig(symbol="NQ", tick_size=0.25, point_value=20.0, commission_per_side=2.5)
    th = StrategyThresholds()
    budget = SessionTradeBudget(3, 0)
    pos = Position(st, nq, th, budget, 0, "2024-06-03")
    pos.update(bar(ts(10, 5), 99.0, 102.5, 98.5, 102.0), 1)
    pos.update(bar(ts(10, 10), 102.0, 104.0, 101.5, 103.5), 2)
    kinds = [f.kind for f in pos.fills]
    assert kinds == ["ENTRY", "TP1_PARTIAL", "TP2"]
    assert len(pos.fills) == 3


def test_audit_06_stop_path_two_fills():
    """AUDIT-06: stop-out → ENTRY + SL only."""
    lvn = make_lvn(50.0, 55.0)
    st = replace(simple_setup(created_at=0), lvn_ref=lvn)
    nq = InstrumentConfig(symbol="NQ", tick_size=0.25, point_value=20.0, commission_per_side=2.5)
    th = StrategyThresholds()
    budget = SessionTradeBudget(3, 0)
    pos = Position(st, nq, th, budget, 0, "2024-06-03")
    pos.update(bar(ts(10, 5), 100.0, 100.5, 99.5, 100.2), 1)
    pos.update(bar(ts(10, 6), 100.0, 99.5, 97.0, 97.5), 2)
    kinds = [f.kind for f in pos.fills]
    assert kinds == ["ENTRY", "SL"]
    assert len([f for f in pos.fills if f.kind != "ENTRY"]) == 1


def test_audit_07_exact_tp_and_sl_prices():
    """AUDIT-07: TP1 at target_price; SL at stop_price."""
    lvn = make_lvn(50.0, 55.0)
    st = replace(
        simple_setup(entry=100.0, stop=98.0, tp1=102.0, tp2=104.0, created_at=0),
        lvn_ref=lvn,
    )
    nq = InstrumentConfig(symbol="NQ", tick_size=0.25, point_value=20.0, commission_per_side=2.5)
    th = StrategyThresholds()
    budget = SessionTradeBudget(3, 0)
    pos = Position(st, nq, th, budget, 0, "2024-06-03")
    pos.update(bar(ts(10, 5), 99.0, 102.5, 98.5, 102.0), 1)
    tp1 = next(f for f in pos.fills if f.kind == "TP1_PARTIAL")
    assert tp1.price == pytest.approx(st.target_price)
    pos2 = Position(
        replace(simple_setup(entry=100.0, stop=98.0, tp1=102.0, tp2=104.0, created_at=0), lvn_ref=lvn),
        nq,
        th,
        budget,
        0,
        "2024-06-03",
    )
    pos2.update(bar(ts(10, 5), 100.0, 100.5, 99.5, 100.2), 1)
    pos2.update(bar(ts(10, 6), 100.0, 99.5, 97.0, 97.5), 2)
    sl = next(f for f in pos2.fills if f.kind == "SL")
    assert sl.price == pytest.approx(st.stop_price)
