"""
Phase 5: TradeSetup contract, fill events, position state machine, PnL helpers.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

import pandas as pd

from src.config import InstrumentConfig, StrategyThresholds
from src.session import WindowConfig

FillEventKind = Literal[
    "ENTRY",
    "TP1_PARTIAL",
    "TP2",
    "SL",
    "BREAKEVEN",
    "HARD_STOP_LVN",
    "EOD",
]


class ExitType(str, Enum):
    FULL_TP = "FULL_TP"
    PARTIAL_TP = "PARTIAL_TP"
    STOP = "STOP"
    HARD_STOP = "HARD_STOP"
    EOD = "EOD"
    TIMEOUT = "TIMEOUT"


class PositionState(str, Enum):
    PENDING_FILL = "PENDING_FILL"
    OPEN_FULL = "OPEN_FULL"
    OPEN_PARTIAL = "OPEN_PARTIAL"
    CLOSED = "CLOSED"


@dataclass(frozen=True)
class ConfidenceAttribution:
    """Snapshot of confidence components at entry (CONFIDENCE_SCORE setups)."""

    total_score: float
    threshold_at_entry: float
    session_bias: str
    direction: Literal["LONG", "SHORT"]
    approach: str
    had_trigger_close: bool
    had_structural: bool
    had_respected_sp: bool
    had_aggressive_window: bool
    contrib_lvn_valid: float
    contrib_bias: float
    contrib_approach: float
    contrib_trigger_close: float
    contrib_structural: float
    contrib_respected_sp: float
    contrib_aggressive_window: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TradeSetup:
    setup_id: str
    entry_price: float
    stop_price: float
    target_price: float
    tp2_price: float
    rr_ratio: float
    direction: Literal["LONG", "SHORT"]
    created_at: int
    setup_type: Literal["THREE_STEP", "AGGRESSIVE_LEDGE", "CONFIDENCE_SCORE"]
    lvn_id: str
    lvn_ref: Any
    ismt_or_smt_ref: Any
    signal_source: Optional[int]
    position_size_scale: float = 1.0
    confidence_attribution: Optional[Dict[str, Any]] = None


@dataclass
class FillEvent:
    bar_index: int
    kind: FillEventKind
    price: float
    contracts: int
    direction: Literal["LONG", "SHORT"]


@dataclass
class TradeResult:
    """EXEC-02 + Phase 5 reporting fields."""

    setup_id: str
    entry_price: float
    stop_price: float
    target_price: float
    tp2_price: float
    rr_ratio: float
    direction: Literal["LONG", "SHORT"]
    created_at: int
    setup_type: Literal["THREE_STEP", "AGGRESSIVE_LEDGE", "CONFIDENCE_SCORE"]
    lvn_id: str
    exit_price_tp1: Optional[float]
    exit_price_tp2: Optional[float]
    exit_type: ExitType
    gross_pnl: float
    net_pnl: float
    total_commission: float
    trade_index: int
    session_date: str
    entry_bar_index: int
    exit_bar_index: int
    signal_source: Optional[int] = None
    position_size_scale: float = 1.0
    confidence_attribution: Optional[Dict[str, Any]] = None


def body_inside_lvn(bar: pd.Series, lvn: Any) -> bool:
    """TP-05: body [min(O,C), max(O,C)] fully inside [lvn.low, lvn.high]."""
    o = float(bar["open_nq"])
    c = float(bar["close_nq"])
    lo, hi = min(o, c), max(o, c)
    return lo >= float(lvn.low) - 1e-9 and hi <= float(lvn.high) + 1e-9


def bar_is_eod(bar: pd.Series) -> bool:
    """TP-06 / D-08: bar time >= 15:45 ET."""
    t = bar.name
    if hasattr(t, "time"):
        return t.time() >= WindowConfig.EOD_CUTOFF
    return False


def compute_position_size(
    entry: float,
    stop: float,
    account_size: float,
    risk_per_trade: float,
    point_value: float,
    position_size_scale: float,
) -> int:
    """EXEC-03."""
    risk_dist = abs(entry - stop)
    if risk_dist <= 0:
        return 0
    raw = (account_size * risk_per_trade) / (risk_dist * point_value)
    full = max(1, int(raw))
    eff = max(1, int(full * position_size_scale))
    return min(eff, full)


def contracts_for_tp1_partial(full: int, pct: float) -> int:
    """TP-03: floor(full×pct), at least 1 contract when full>=1."""
    if full <= 0:
        return 0
    if full == 1:
        return 1
    n = max(1, int(full * pct))
    return min(n, full)


@dataclass
class SessionTradeBudget:
    """D-03: count opens on transition to OPEN_FULL."""

    max_trades: int = 3
    opens_this_session: int = 0

    def can_enter(self) -> bool:
        return self.opens_this_session < self.max_trades

    def on_open_full(self) -> None:
        self.opens_this_session += 1


def total_commission_from_fills(fills: List[FillEvent], commission_per_side: float) -> float:
    """EXEC-05: per fill event."""
    return sum(f.contracts * commission_per_side for f in fills)


def fills_to_gross_pnl(
    fills: List[FillEvent],
    setup: TradeSetup,
    point_value: float,
) -> float:
    """EXEC-04 / P4 — long vs short from entry vs exit prices."""
    entry_px = setup.entry_price
    gross = 0.0
    for f in fills:
        if f.kind == "ENTRY":
            continue
        if setup.direction == "LONG":
            gross += (f.price - entry_px) * f.contracts * point_value
        else:
            gross += (entry_px - f.price) * f.contracts * point_value
    return gross


def infer_exit_type(fills: List[FillEvent]) -> ExitType:
    kinds = {f.kind for f in fills}
    if "EOD" in kinds:
        return ExitType.EOD
    if "HARD_STOP_LVN" in kinds:
        return ExitType.HARD_STOP
    if "SL" in kinds and "TP1_PARTIAL" not in kinds:
        return ExitType.STOP
    if "TP2" in kinds:
        if "TP1_PARTIAL" in kinds:
            return ExitType.PARTIAL_TP
        return ExitType.FULL_TP
    if "TP1_PARTIAL" in kinds:
        return ExitType.PARTIAL_TP
    if "BREAKEVEN" in kinds:
        return ExitType.PARTIAL_TP
    if "SL" in kinds:
        return ExitType.STOP
    return ExitType.TIMEOUT


def build_trade_result(
    setup: TradeSetup,
    fills: List[FillEvent],
    instrument: InstrumentConfig,
    trade_index: int,
    session_date: str,
    entry_bar_index: int,
    exit_bar_index: int,
) -> TradeResult:
    comm = total_commission_from_fills(fills, instrument.commission_per_side)
    gross = fills_to_gross_pnl(fills, setup, instrument.point_value)
    net = gross - comm
    et = infer_exit_type(fills)
    tp1_px = next((f.price for f in fills if f.kind == "TP1_PARTIAL"), None)
    tp2_px = None
    for f in fills:
        if f.kind in ("TP2", "BREAKEVEN", "SL", "HARD_STOP_LVN", "EOD"):
            if f.kind != "TP1_PARTIAL":
                tp2_px = f.price
    if tp2_px is None and tp1_px is not None:
        for f in reversed(fills):
            if f.kind != "ENTRY":
                tp2_px = f.price
                break
    return TradeResult(
        setup_id=setup.setup_id,
        entry_price=setup.entry_price,
        stop_price=setup.stop_price,
        target_price=setup.target_price,
        tp2_price=setup.tp2_price,
        rr_ratio=setup.rr_ratio,
        direction=setup.direction,
        created_at=setup.created_at,
        setup_type=setup.setup_type,
        lvn_id=setup.lvn_id,
        exit_price_tp1=tp1_px,
        exit_price_tp2=tp2_px,
        exit_type=et,
        gross_pnl=gross,
        net_pnl=net,
        total_commission=comm,
        trade_index=trade_index,
        session_date=session_date,
        entry_bar_index=entry_bar_index,
        exit_bar_index=exit_bar_index,
        signal_source=setup.signal_source,
        position_size_scale=setup.position_size_scale,
        confidence_attribution=setup.confidence_attribution,
    )


def enter_from_setup(setup: TradeSetup, aggressive_state: Optional[Any] = None) -> None:
    """Phase 4 hook; real open is via Position (Phase 5)."""
    if setup.setup_type == "AGGRESSIVE_LEDGE":
        from src import entry as entry_mod

        st = aggressive_state or entry_mod.AggressiveLvnState()
        entry_mod.notify_aggressive_trade_completed(setup.lvn_id, st)
    raise NotImplementedError("Use Position.update for execution")


class Position:
    """Bar-by-bar position state machine (D-01–D-08)."""

    def __init__(
        self,
        setup: TradeSetup,
        instrument: InstrumentConfig,
        thresholds: StrategyThresholds,
        budget: SessionTradeBudget,
        trade_index: int = 0,
        session_date: str = "",
    ):
        self.setup = setup
        self.instrument = instrument
        self.thresholds = thresholds
        self.budget = budget
        self.trade_index = trade_index
        self.session_date = session_date or date.today().isoformat()
        self.state = PositionState.PENDING_FILL
        self.remaining = 0
        self.stop_price = setup.stop_price
        self.fills: List[FillEvent] = []
        self.entry_bar_index: int = -1
        self._bar_index = -1

    def _append(self, bar_index: int, kind: FillEventKind, price: float, contracts: int) -> FillEvent:
        ev = FillEvent(
            bar_index=bar_index,
            kind=kind,
            price=price,
            contracts=contracts,
            direction=self.setup.direction,
        )
        self.fills.append(ev)
        return ev

    def update(self, bar: pd.Series, bar_index: int) -> List[FillEvent]:
        self._bar_index = bar_index
        out: List[FillEvent] = []

        if self.state == PositionState.CLOSED:
            return out

        if self.state == PositionState.PENDING_FILL:
            # Wait until the signal bar. Must run BEFORE bar_is_eod: session_df is full Globex
            # (often starts ~18:00 prior day). Times >= 15:45 are "EOD" for bar_is_eod, so
            # evening bars would otherwise clear PENDING_FILL with no ENTRY before RTH.
            if bar_index < self.setup.created_at:
                return out
            # No new entries at/after RTH flat time on the signal bar.
            if bar_is_eod(bar):
                self.state = PositionState.CLOSED
                return out
            if not self.budget.can_enter():
                self.state = PositionState.CLOSED
                return out
            size = compute_position_size(
                self.setup.entry_price,
                self.setup.stop_price,
                self.thresholds.account_size,
                self.thresholds.risk_per_trade,
                self.instrument.point_value,
                self.setup.position_size_scale,
            )
            if size <= 0:
                self.state = PositionState.CLOSED
                return out
            self.remaining = size
            self.budget.on_open_full()
            self.entry_bar_index = bar_index
            out.append(
                self._append(
                    bar_index,
                    "ENTRY",
                    self.setup.entry_price,
                    self.remaining,
                )
            )
            self.state = PositionState.OPEN_FULL
            # Continue same bar for TP/SL (intrabar after entry)
            more = self._update_open(bar, bar_index)
            return out + more

        if self.state in (PositionState.OPEN_FULL, PositionState.OPEN_PARTIAL):
            return self._update_open(bar, bar_index)

        return out

    def force_end_of_session_flat(self, bar: pd.Series, bar_index: int) -> List[FillEvent]:
        """
        If the dataframe ends before a 15:45+ EOD bar fires, still flatten at the last bar close.
        Without this, ``to_trade_result()`` stays None while ENTRY exists (open positions).
        """
        if self.state not in (PositionState.OPEN_FULL, PositionState.OPEN_PARTIAL):
            return []
        if self.remaining <= 0:
            self.state = PositionState.CLOSED
            return []
        out = [
            self._append(
                bar_index,
                "EOD",
                float(bar["close_nq"]),
                self.remaining,
            )
        ]
        self.remaining = 0
        self.state = PositionState.CLOSED
        return out

    def _update_open(self, bar: pd.Series, bar_index: int) -> List[FillEvent]:
        out: List[FillEvent] = []
        if self.state == PositionState.CLOSED:
            return out

        # 1) EOD
        if bar_is_eod(bar):
            px = float(bar["close_nq"])
            out.append(self._append(bar_index, "EOD", px, self.remaining))
            self.remaining = 0
            self.state = PositionState.CLOSED
            return out

        # 2) Hard stop LVN
        if body_inside_lvn(bar, self.setup.lvn_ref):
            px = float(bar["close_nq"])
            out.append(self._append(bar_index, "HARD_STOP_LVN", px, self.remaining))
            self.remaining = 0
            self.state = PositionState.CLOSED
            return out

        # 3) TP / SL path
        if self.setup.direction == "LONG":
            return out + self._update_long_path(bar, bar_index)
        return out + self._update_short_path(bar, bar_index)

    def _update_long_path(self, bar: pd.Series, bar_index: int) -> List[FillEvent]:
        out: List[FillEvent] = []
        hi = float(bar["high_nq"])
        lo = float(bar["low_nq"])
        tp1 = self.setup.target_price
        tp2 = self.setup.tp2_price
        entry = self.setup.entry_price

        if self.state == PositionState.OPEN_FULL:
            hit_tp1 = hi >= tp1
            hit_sl = lo <= self.stop_price
            if hit_tp1 and hit_sl:
                n = contracts_for_tp1_partial(
                    self.remaining, self.thresholds.take_profit_1_exit_pct
                )
                out.append(self._append(bar_index, "TP1_PARTIAL", tp1, n))
                self.remaining -= n
                self.stop_price = entry
                if self.remaining <= 0:
                    self.state = PositionState.CLOSED
                    return out
                self.state = PositionState.OPEN_PARTIAL
                if lo <= entry:
                    out.append(self._append(bar_index, "BREAKEVEN", entry, self.remaining))
                    self.remaining = 0
                    self.state = PositionState.CLOSED
                return out
            if hit_sl:
                out.append(self._append(bar_index, "SL", self.stop_price, self.remaining))
                self.remaining = 0
                self.state = PositionState.CLOSED
                return out
            if hit_tp1:
                n = contracts_for_tp1_partial(
                    self.remaining, self.thresholds.take_profit_1_exit_pct
                )
                out.append(self._append(bar_index, "TP1_PARTIAL", tp1, n))
                self.remaining -= n
                if self.remaining <= 0:
                    self.state = PositionState.CLOSED
                    return out
                self.stop_price = entry
                self.state = PositionState.OPEN_PARTIAL
                return out
            return out

        # OPEN_PARTIAL long: TP2 before breakeven SL (D-06 symmetry)
        hit_tp2 = hi >= tp2
        hit_be = lo <= self.stop_price
        if hit_tp2 and hit_be:
            out.append(self._append(bar_index, "TP2", tp2, self.remaining))
            self.remaining = 0
            self.state = PositionState.CLOSED
            return out
        if hit_tp2:
            out.append(self._append(bar_index, "TP2", tp2, self.remaining))
            self.remaining = 0
            self.state = PositionState.CLOSED
            return out
        if hit_be:
            out.append(self._append(bar_index, "SL", self.stop_price, self.remaining))
            self.remaining = 0
            self.state = PositionState.CLOSED
            return out
        return out

    def _update_short_path(self, bar: pd.Series, bar_index: int) -> List[FillEvent]:
        out: List[FillEvent] = []
        hi = float(bar["high_nq"])
        lo = float(bar["low_nq"])
        tp1 = self.setup.target_price
        tp2 = self.setup.tp2_price
        entry = self.setup.entry_price

        if self.state == PositionState.OPEN_FULL:
            hit_tp1 = lo <= tp1
            hit_sl = hi >= self.stop_price
            if hit_tp1 and hit_sl:
                n = contracts_for_tp1_partial(
                    self.remaining, self.thresholds.take_profit_1_exit_pct
                )
                out.append(self._append(bar_index, "TP1_PARTIAL", tp1, n))
                self.remaining -= n
                self.stop_price = entry
                if self.remaining <= 0:
                    self.state = PositionState.CLOSED
                    return out
                self.state = PositionState.OPEN_PARTIAL
                if hi >= entry:
                    out.append(self._append(bar_index, "BREAKEVEN", entry, self.remaining))
                    self.remaining = 0
                    self.state = PositionState.CLOSED
                return out
            if hit_sl:
                out.append(self._append(bar_index, "SL", self.stop_price, self.remaining))
                self.remaining = 0
                self.state = PositionState.CLOSED
                return out
            if hit_tp1:
                n = contracts_for_tp1_partial(
                    self.remaining, self.thresholds.take_profit_1_exit_pct
                )
                out.append(self._append(bar_index, "TP1_PARTIAL", tp1, n))
                self.remaining -= n
                if self.remaining <= 0:
                    self.state = PositionState.CLOSED
                    return out
                self.stop_price = entry
                self.state = PositionState.OPEN_PARTIAL
                return out
            return out

        hit_tp2 = lo <= tp2
        hit_be = hi >= self.stop_price
        if hit_tp2 and hit_be:
            out.append(self._append(bar_index, "TP2", tp2, self.remaining))
            self.remaining = 0
            self.state = PositionState.CLOSED
            return out
        if hit_tp2:
            out.append(self._append(bar_index, "TP2", tp2, self.remaining))
            self.remaining = 0
            self.state = PositionState.CLOSED
            return out
        if hit_be:
            out.append(self._append(bar_index, "SL", self.stop_price, self.remaining))
            self.remaining = 0
            self.state = PositionState.CLOSED
            return out
        return out

    def to_trade_result(self) -> Optional[TradeResult]:
        if self.state != PositionState.CLOSED or not self.fills:
            return None
        exit_idx = max(f.bar_index for f in self.fills)
        return build_trade_result(
            self.setup,
            self.fills,
            self.instrument,
            self.trade_index,
            self.session_date,
            self.entry_bar_index,
            exit_idx,
        )
