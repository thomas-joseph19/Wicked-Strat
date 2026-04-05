"""Phase 7 — fixtures for backtest wiring tests."""

import pytest

from src.config import InstrumentConfig, StrategyThresholds


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
