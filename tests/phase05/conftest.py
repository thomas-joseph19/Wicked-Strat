"""Phase 5 test factories."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, List
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from src.config import InstrumentConfig, StrategyThresholds
from src.lvn import LVNZone
from src.position import SessionTradeBudget, TradeSetup

NY = ZoneInfo("America/New_York")


def ts(h: int, m: int, d: int = 3, month: int = 6, year: int = 2024) -> pd.Timestamp:
    return pd.Timestamp(datetime(year, month, d, h, m), tz=NY)


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


@pytest.fixture
def session_budget() -> SessionTradeBudget:
    return SessionTradeBudget(max_trades=3, opens_this_session=0)


def make_lvn(low: float, high: float) -> LVNZone:
    mid = (low + high) / 2
    return LVNZone(
        low=low,
        high=high,
        midpoint=mid,
        width_ticks=int(round((high - low) / 0.25)),
        strength=0.5,
        session_id="t",
        valid=True,
    )


@dataclass
class SP:
    low: float
    high: float
    respected_overnight: bool = True


def bar(
    t: pd.Timestamp,
    o: float,
    h: float,
    l: float,
    c: float,
) -> pd.Series:
    return pd.Series(
        {
            "open_nq": o,
            "high_nq": h,
            "low_nq": l,
            "close_nq": c,
            "open_es": o,
            "high_es": h,
            "low_es": l,
            "close_es": c,
            "is_synthetic_nq": False,
            "is_synthetic_es": False,
            "is_synthetic": False,
        },
        name=t,
    )


def simple_setup(
    *,
    entry: float = 100.0,
    stop: float = 98.0,
    tp1: float = 102.0,
    tp2: float = 104.0,
    direction: str = "LONG",
    created_at: int = 0,
) -> TradeSetup:
    return TradeSetup(
        setup_id="test",
        entry_price=entry,
        stop_price=stop,
        target_price=tp1,
        tp2_price=tp2,
        rr_ratio=1.0,
        direction=direction,  # type: ignore
        created_at=created_at,
        setup_type="THREE_STEP",
        lvn_id="1",
        # Far from default entry (100) so body_inside_lvn does not fire in generic TP/SL tests.
        lvn_ref=make_lvn(50.0, 55.0),
        ismt_or_smt_ref=None,
        signal_source=1,
        position_size_scale=1.0,
    )
