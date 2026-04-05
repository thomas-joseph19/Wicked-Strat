"""
Entry evaluation: structural confirmation (D-04–D-06), 3-Step, Aggressive Ledge, ENTRY-05.
TradeSetup lives in src.position (EXEC-01).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import time
from typing import Any, List, Literal, Optional, Sequence, Tuple, Union

import pandas as pd

from src.ismt import IsmtSignal
from src.lvn import LVNZone
from src.position import TradeSetup
from src.session import WindowConfig
from src.smt import SmtSignal


@dataclass
class AggressiveLvnState:
    aggressive_lvn_pending_suppression: set = field(default_factory=set)
    aggressive_lvn_suppressed_for_session: set = field(default_factory=set)
    setups_emitted_this_session: int = 0


def notify_aggressive_trade_completed(lvn_id: str, state: AggressiveLvnState) -> None:
    state.aggressive_lvn_pending_suppression.discard(lvn_id)
    state.aggressive_lvn_suppressed_for_session.add(lvn_id)


def signal_source_value(sig: Union[IsmtSignal, SmtSignal]) -> int:
    return 1 if isinstance(sig, IsmtSignal) or getattr(sig, "signal_kind", None) == "ISMT" else 0


def get_structural_confirmation(
    direction: Literal["BULLISH", "BEARISH"],
    current_bar_index: int,
    ismt_signals: Sequence[IsmtSignal],
    smt_signals: Sequence[SmtSignal],
) -> Union[IsmtSignal, SmtSignal, None]:
    """
    D-05: confirmed_at in [i-4, i] inclusive.
    D-04: max confirmed_at; tie → prefer SMT (plan 04-03).
    D-06: drop invalidated.
    """
    want = "LONG" if direction == "BULLISH" else "SHORT"
    lo = current_bar_index - 4
    candidates: List[Union[IsmtSignal, SmtSignal]] = []
    for s in ismt_signals:
        if s.invalidated or s.direction != want:
            continue
        if lo <= s.confirmed_at <= current_bar_index:
            candidates.append(s)
    for s in smt_signals:
        if s.invalidated or s.direction != want:
            continue
        if lo <= s.confirmed_at <= current_bar_index:
            candidates.append(s)
    if not candidates:
        return None

    def sort_key(x: Union[IsmtSignal, SmtSignal]) -> Tuple[int, int]:
        # larger confirmed_at first; tie: SMT (0) before ISMT (1) so SMT wins
        is_smt = 0 if isinstance(x, SmtSignal) else 1
        return (x.confirmed_at, -is_smt)

    candidates.sort(key=sort_key, reverse=True)
    return candidates[0]


def lvn_stable_id(lvn: LVNZone, tick_size: float = 0.25) -> str:
    snapped = round(lvn.midpoint / tick_size) * tick_size
    return f"{snapped:.4f}"


def approaches_lvn_long(bar: pd.Series, prior_bars: List[pd.Series], lvn: LVNZone, tick_size: float = 0.25) -> bool:
    """D-08: touch + prior 3 closes strictly above LVN.high."""
    if lvn is None or not lvn.valid:
        return False
    if len(prior_bars) < 3:
        return False
    buf = 3.0 * tick_size
    closes = [b["close_nq"] for b in prior_bars[-3:]]
    if not all(c > lvn.high for c in closes):
        return False
    return bar["low_nq"] <= lvn.high + buf


def approaches_lvn_short(bar: pd.Series, prior_bars: List[pd.Series], lvn: LVNZone, tick_size: float = 0.25) -> bool:
    """D-09."""
    if lvn is None or not lvn.valid:
        return False
    if len(prior_bars) < 3:
        return False
    buf = 3.0 * tick_size
    closes = [b["close_nq"] for b in prior_bars[-3:]]
    if not all(c < lvn.low for c in closes):
        return False
    return bar["high_nq"] >= lvn.low - buf


def snap_tick(price: float, tick_size: float = 0.25) -> float:
    return round(price / tick_size) * tick_size


def compute_sl_tp1_long(lvn: LVNZone, atr5: float, sp_zones: Sequence[Any], entry: float) -> Tuple[float, float]:
    """SL-01 long; TP1 = bottom of nearest respected SP above entry (TP-01)."""
    stop = snap_tick(lvn.low - 0.5 * atr5)
    tp1 = entry + 20.0  # fallback if no SP
    best = None
    for sp in sp_zones:
        if getattr(sp, "respected_overnight", False) and sp.low > entry:
            if best is None or sp.low < best.low:
                best = sp
    if best is not None:
        tp1 = best.low
    return stop, tp1


def compute_sl_tp1_short(lvn: LVNZone, atr5: float, sp_zones: Sequence[Any], entry: float) -> Tuple[float, float]:
    stop = snap_tick(lvn.high + 0.5 * atr5)
    tp1 = entry - 20.0
    best = None
    for sp in sp_zones:
        if getattr(sp, "respected_overnight", False) and sp.high < entry:
            if best is None or sp.high > best.high:
                best = sp
    if best is not None:
        tp1 = best.high
    return stop, tp1


def validate_pre_entry(
    *,
    entry_price: float,
    stop_price: float,
    target_price: float,
    bias: str,
    atr20: float,
    tick_size: float,
    bar_time: time,
    session_setup_count: int,
) -> bool:
    """ENTRY-05 + time/counters."""
    if session_setup_count >= 3:
        return False
    if bias == "NEUTRAL":
        return False
    if bar_time >= time(15, 45):
        return False
    risk = abs(entry_price - stop_price)
    reward = abs(target_price - entry_price)
    if risk <= 0:
        return False
    if reward / risk < 1.5:
        return False
    risk_ticks = risk / tick_size
    max_ticks = 1.5 * atr20 / tick_size
    if risk_ticks < 4 or risk_ticks > max_ticks + 1e-9:
        return False
    return True


def build_trade_setup(
    *,
    bar_index: int,
    bar: pd.Series,
    direction: Literal["LONG", "SHORT"],
    setup_type: Literal["THREE_STEP", "AGGRESSIVE_LEDGE"],
    lvn: LVNZone,
    structural: Optional[Union[IsmtSignal, SmtSignal]],
    atr5: float,
    atr20: float,
    sp_zones: Sequence[Any],
    tick_size: float = 0.25,
) -> TradeSetup:
    entry_price = float(bar["close_nq"])
    if direction == "LONG":
        stop_price, target_price = compute_sl_tp1_long(lvn, atr5, sp_zones, entry_price)
    else:
        stop_price, target_price = compute_sl_tp1_short(lvn, atr5, sp_zones, entry_price)
    risk = abs(entry_price - stop_price)
    reward = abs(target_price - entry_price)
    rr = reward / risk if risk > 0 else 0.0
    sig_src = signal_source_value(structural) if structural is not None else None
    scale = 0.5 if setup_type == "AGGRESSIVE_LEDGE" else 1.0
    lid = lvn_stable_id(lvn, tick_size)
    return TradeSetup(
        setup_id=str(uuid.uuid4())[:12],
        entry_price=entry_price,
        stop_price=stop_price,
        target_price=target_price,
        rr_ratio=rr,
        direction=direction,
        created_at=bar_index,
        setup_type=setup_type,
        lvn_id=lid,
        lvn_ref=lvn,
        ismt_or_smt_ref=structural,
        signal_source=sig_src,
        position_size_scale=scale,
    )


def evaluate_three_step_long(
    i: int,
    bar: pd.Series,
    prior_bars: List[pd.Series],
    lvn: LVNZone,
    sp_zones: Sequence[Any],
    ismt_signals: Sequence[IsmtSignal],
    smt_signals: Sequence[SmtSignal],
    atr5: float,
    atr20: float,
    tick_size: float = 0.25,
) -> Optional[TradeSetup]:
    if not lvn.valid:
        return None

    if not approaches_lvn_long(bar, prior_bars, lvn, tick_size):
        return None
    if bar["close_nq"] <= lvn.high or bar["close_nq"] <= bar["open_nq"]:
        return None
    struct = get_structural_confirmation("BULLISH", i, ismt_signals, smt_signals)
    if struct is None:
        return None
    entry_price = float(bar["close_nq"])
    ok_sp = any(
        getattr(sp, "respected_overnight", False) and sp.low > entry_price for sp in sp_zones
    )
    if not ok_sp:
        return None
    return build_trade_setup(
        bar_index=i,
        bar=bar,
        direction="LONG",
        setup_type="THREE_STEP",
        lvn=lvn,
        structural=struct,
        atr5=atr5,
        atr20=atr20,
        sp_zones=sp_zones,
        tick_size=tick_size,
    )


def evaluate_three_step_short(
    i: int,
    bar: pd.Series,
    prior_bars: List[pd.Series],
    lvn: LVNZone,
    sp_zones: Sequence[Any],
    ismt_signals: Sequence[IsmtSignal],
    smt_signals: Sequence[SmtSignal],
    atr5: float,
    atr20: float,
    tick_size: float = 0.25,
) -> Optional[TradeSetup]:
    if not lvn.valid:
        return None
    if not approaches_lvn_short(bar, prior_bars, lvn, tick_size):
        return None
    if bar["close_nq"] >= lvn.low or bar["close_nq"] >= bar["open_nq"]:
        return None
    struct = get_structural_confirmation("BEARISH", i, ismt_signals, smt_signals)
    if struct is None:
        return None
    entry_price = float(bar["close_nq"])
    ok_sp = any(
        getattr(sp, "respected_overnight", False) and sp.high < entry_price for sp in sp_zones
    )
    if not ok_sp:
        return None
    return build_trade_setup(
        bar_index=i,
        bar=bar,
        direction="SHORT",
        setup_type="THREE_STEP",
        lvn=lvn,
        structural=struct,
        atr5=atr5,
        atr20=atr20,
        sp_zones=sp_zones,
        tick_size=tick_size,
    )


def evaluate_aggressive_long(
    i: int,
    bar: pd.Series,
    lvn: LVNZone,
    bias: str,
    atr5: float,
    atr20: float,
    sp_zones: Sequence[Any],
    state: AggressiveLvnState,
    tick_size: float = 0.25,
) -> Optional[TradeSetup]:
    if not lvn.valid:
        return None
    lid = lvn_stable_id(lvn, tick_size)
    if lid in state.aggressive_lvn_suppressed_for_session:
        return None
    t = bar.name
    if hasattr(t, "time"):
        bt = t.time()
    else:
        bt = time(9, 45)
    if not (WindowConfig.AGGRESSIVE_START <= bt <= WindowConfig.AGGRESSIVE_END):
        return None
    if bias != "BULLISH":
        return None
    c = bar["close_nq"]
    dist = min(abs(c - lvn.low), abs(c - lvn.high))
    if dist > 3 * tick_size + 1e-9:
        return None
    if c <= lvn.high or bar["close_nq"] <= bar["open_nq"]:
        return None
    setup = build_trade_setup(
        bar_index=i,
        bar=bar,
        direction="LONG",
        setup_type="AGGRESSIVE_LEDGE",
        lvn=lvn,
        structural=None,
        atr5=atr5,
        atr20=atr20,
        sp_zones=sp_zones,
        tick_size=tick_size,
    )
    setup.ismt_or_smt_ref = None
    setup.signal_source = None
    return setup


def evaluate_aggressive_short(
    i: int,
    bar: pd.Series,
    lvn: LVNZone,
    bias: str,
    atr5: float,
    atr20: float,
    sp_zones: Sequence[Any],
    state: AggressiveLvnState,
    tick_size: float = 0.25,
) -> Optional[TradeSetup]:
    if not lvn.valid:
        return None
    lid = lvn_stable_id(lvn, tick_size)
    if lid in state.aggressive_lvn_suppressed_for_session:
        return None
    t = bar.name
    bt = t.time() if hasattr(t, "time") else time(9, 45)
    if not (WindowConfig.AGGRESSIVE_START <= bt <= WindowConfig.AGGRESSIVE_END):
        return None
    if bias != "BEARISH":
        return None
    c = bar["close_nq"]
    dist = min(abs(c - lvn.low), abs(c - lvn.high))
    if dist > 3 * tick_size + 1e-9:
        return None
    if c >= lvn.low or bar["close_nq"] >= bar["open_nq"]:
        return None
    setup = build_trade_setup(
        bar_index=i,
        bar=bar,
        direction="SHORT",
        setup_type="AGGRESSIVE_LEDGE",
        lvn=lvn,
        structural=None,
        atr5=atr5,
        atr20=atr20,
        sp_zones=sp_zones,
        tick_size=tick_size,
    )
    setup.ismt_or_smt_ref = None
    setup.signal_source = None
    return setup


def register_aggressive_pending(setup: TradeSetup, state: AggressiveLvnState) -> None:
    if setup.setup_type == "AGGRESSIVE_LEDGE":
        state.aggressive_lvn_pending_suppression.add(setup.lvn_id)


class EntryEngine:
    """Legacy-style facade; prefer module-level functions for tests."""

    def __init__(self, thresholds: Any = None):
        self.thresholds = thresholds
        self.aggressive_state = AggressiveLvnState()

    def get_structural_confirmation(
        self,
        current_idx: int,
        ismt_signals: Sequence[IsmtSignal],
        smt_signals: Sequence[SmtSignal],
        direction: Literal["BULLISH", "BEARISH"] = "BULLISH",
    ):
        return get_structural_confirmation(direction, current_idx, ismt_signals, smt_signals)
