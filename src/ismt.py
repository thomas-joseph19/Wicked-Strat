"""
ISMT (single-instrument) detection on NQ. Bar-close only; window anchored to SH2/SL2 confirmed_at (D-01/D-02).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Literal, Optional, Sequence, Tuple

from src.swings import SwingPoint


@dataclass
class IsmtSignal:
    direction: Literal["LONG", "SHORT"]
    confirmed_at: int
    sweep_size: float
    entry_zone: float
    source_swings: Tuple[SwingPoint, ...]
    signal_kind: Literal["ISMT"] = "ISMT"
    invalidated: bool = False


def detect_ismt_at_bar(
    j: int,
    close_nq: float,
    atr20_at_j: float,
    swings: Sequence[SwingPoint],
) -> Optional[IsmtSignal]:
    """
    Evaluate bar index j (bar just closed). Only swings with confirmed_at <= j are visible.

    Bearish: last two HIGH swings SH1, SH2 with SH2.price > SH1.price,
    1 <= SH2.confirmed_at - SH1.confirmed_at <= 10,
    first bar in [SH2.confirmed_at+1, SH2.confirmed_at+3] where close < SH1.price wins (earliest j).
    """
    highs = [s for s in swings if s.direction == "HIGH" and s.confirmed_at <= j]
    lows = [s for s in swings if s.direction == "LOW" and s.confirmed_at <= j]

    # Bearish (SHORT)
    if len(highs) >= 2:
        sh1, sh2 = highs[-2], highs[-1]
        t = sh2.confirmed_at
        if sh2.price > sh1.price and 1 <= (sh2.confirmed_at - sh1.confirmed_at) <= 10:
            sweep = sh2.price - sh1.price
            if (
                sweep < 2.0 * atr20_at_j
                and t + 1 <= j <= t + 3
                and close_nq < sh1.price
            ):
                return IsmtSignal(
                    direction="SHORT",
                    confirmed_at=j,
                    sweep_size=sweep,
                    entry_zone=sh1.price,
                    source_swings=(sh1, sh2),
                )

    # Bullish (LONG)
    if len(lows) >= 2:
        sl1, sl2 = lows[-2], lows[-1]
        t = sl2.confirmed_at
        if sl2.price < sl1.price and 1 <= (sl2.confirmed_at - sl1.confirmed_at) <= 10:
            sweep = sl1.price - sl2.price
            if (
                sweep < 2.0 * atr20_at_j
                and t + 1 <= j <= t + 3
                and close_nq > sl1.price
            ):
                return IsmtSignal(
                    direction="LONG",
                    confirmed_at=j,
                    sweep_size=sweep,
                    entry_zone=sl1.price,
                    source_swings=(sl1, sl2),
                )

    return None


def invalidate_ismt_if_trade_through(signal: IsmtSignal, bars_closes: Sequence[float], from_j: int) -> IsmtSignal:
    """After signal at from_j, if any subsequent close invalidates structure, mark invalidated."""
    if signal.direction == "SHORT":
        sh1 = signal.source_swings[0]
        for k in range(from_j + 1, len(bars_closes)):
            if bars_closes[k] > sh1.price:
                signal.invalidated = True
                break
    elif signal.direction == "LONG":
        sl1 = signal.source_swings[0]
        for k in range(from_j + 1, len(bars_closes)):
            if bars_closes[k] < sl1.price:
                signal.invalidated = True
                break
    return signal
