"""Shared fixtures for Phase 4 tests (bars, swings, LVN, sync stream rows)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

import pandas as pd

from src.lvn import LVNZone
from src.swings import SwingPoint

NY = ZoneInfo("America/New_York")

TICK_SIZE = 0.25


def ts(h: int, m: int, d: int = 1, month: int = 6, year: int = 2024) -> pd.Timestamp:
    return pd.Timestamp(datetime(year, month, d, h, m), tz=NY)


def make_swing(
    bar_index: int,
    confirmed_at: int,
    price: float,
    direction: str,
    timestamp: pd.Timestamp | None = None,
) -> SwingPoint:
    t = timestamp if timestamp is not None else ts(10, 0)
    return SwingPoint(
        bar_index=bar_index,
        timestamp=t,
        price=price,
        direction=direction,
        confirmed_at=confirmed_at,
        confirmed_time=t,
    )


def make_lvn(low: float, high: float, valid: bool = True, session_id: str = "test") -> LVNZone:
    mid = (low + high) / 2.0
    width_ticks = int(round((high - low) / TICK_SIZE))
    return LVNZone(
        low=low,
        high=high,
        midpoint=mid,
        width_ticks=max(1, width_ticks),
        strength=0.5,
        session_id=session_id,
        valid=valid,
    )


@dataclass
class SPZone:
    low: float
    high: float
    respected_overnight: bool = True


def make_sp_zone(low: float, high: float, respected_overnight: bool = True) -> SPZone:
    return SPZone(low=low, high=high, respected_overnight=respected_overnight)


def make_bar_row(
    i: int,
    o: float,
    h: float,
    l: float,
    c: float,
    timestamp: pd.Timestamp | None = None,
    atr_fast: float = 2.0,
    atr_slow: float = 4.0,
) -> pd.Series:
    t = timestamp if timestamp is not None else ts(10, 30) + pd.Timedelta(minutes=i)
    idx = t
    data: Dict[str, Any] = {
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
        "atr_fast": atr_fast,
        "atr_slow": atr_slow,
    }
    return pd.Series(data, name=idx)


def bars_from_rows(rows: List[Dict[str, Any]]) -> List[pd.Series]:
    out: List[pd.Series] = []
    for r in rows:
        ts_val = r.get("timestamp", ts(9, 30))
        s = pd.Series(
            {
                "open_nq": r["open"],
                "high_nq": r["high"],
                "low_nq": r["low"],
                "close_nq": r["close"],
                "open_es": r.get("open_es", r["open"]),
                "high_es": r.get("high_es", r["high"]),
                "low_es": r.get("low_es", r["low"]),
                "close_es": r.get("close_es", r["close"]),
                "is_synthetic_nq": r.get("is_synthetic_nq", False),
                "is_synthetic_es": r.get("is_synthetic_es", False),
                "is_synthetic": r.get(
                    "is_synthetic",
                    r.get("is_synthetic_nq", False) or r.get("is_synthetic_es", False),
                ),
                "atr_fast": r.get("atr_fast", 2.0),
                "atr_slow": r.get("atr_slow", 4.0),
            },
            name=ts_val,
        )
        out.append(s)
    return out
