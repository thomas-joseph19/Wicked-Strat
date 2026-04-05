"""Factories for TradeResult metrics tests."""

from __future__ import annotations

import pytest

from src.config import InstrumentConfig, StrategyThresholds
from src.position import ExitType, TradeResult


@pytest.fixture
def nq_instrument() -> InstrumentConfig:
    return InstrumentConfig(
        symbol="NQ",
        tick_size=0.25,
        point_value=20.0,
        commission_per_side=2.50,
    )


@pytest.fixture
def thresholds() -> StrategyThresholds:
    return StrategyThresholds()


def make_trade(
    *,
    session_date: str = "2024-06-03",
    net_pnl: float = 100.0,
    setup_type: str = "THREE_STEP",
    signal_source: int | None = 1,
    exit_type: ExitType = ExitType.FULL_TP,
    trade_index: int = 0,
) -> TradeResult:
    return TradeResult(
        setup_id="t",
        entry_price=100.0,
        stop_price=99.0,
        target_price=102.0,
        tp2_price=104.0,
        rr_ratio=1.0,
        direction="LONG",
        created_at=0,
        setup_type=setup_type,  # type: ignore[arg-type]
        lvn_id="1",
        exit_price_tp1=None,
        exit_price_tp2=103.0,
        exit_type=exit_type,
        gross_pnl=net_pnl + 10,
        net_pnl=net_pnl,
        total_commission=10.0,
        trade_index=trade_index,
        session_date=session_date,
        entry_bar_index=1,
        exit_bar_index=2,
        signal_source=signal_source,
        position_size_scale=1.0,
    )
