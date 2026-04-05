"""
ISMT — single-instrument market structure trap (NQ only), bar-close.

**Idea:** After a *second* swing in the same direction extends beyond the prior swing (micro BOS), the
*first* swing's extreme is used as the trap level; if price *reclaims* through that level within a tight
window, flag a directional ISMT (liquidity sweep + rejection read).

**Math (bearish / SHORT):**
- Take last two confirmed *high* swings SH1, SH2 with SH2.price > SH1.price (higher high).
- Spacing: 1 ≤ SH2.confirmed_at − SH1.confirmed_at ≤ 10 bars.
- Sweep size SH2 − SH1 must be < 2 × ATR(20) at the evaluation bar (cap huge news spikes).
- On bar index ``j`` only if SH2.confirmed_at + 1 ≤ j ≤ SH2.confirmed_at + 3 and close_nq < SH1.price
  (close back below the trapped high → bearish confirmation).

**Bullish (LONG):** symmetric on two *low* swings with SL2.price < SL1.price and close > SL1.price.

``confirmed_at`` is set to ``j`` (the bar where the reclaim is detected) so it aligns with
``get_structural_confirmation``'s recent window [i−4, i] when entries are evaluated on the same bar.
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
