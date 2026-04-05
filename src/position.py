"""
Position / execution stubs (Phase 5). TradeSetup is the Phase 4 → Phase 5 contract.
Direction convention: LONG / SHORT (aligns with IsmtSignal / SmtSignal).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Optional


@dataclass
class TradeSetup:
    setup_id: str
    entry_price: float
    stop_price: float
    target_price: float
    rr_ratio: float
    direction: Literal["LONG", "SHORT"]
    created_at: int
    setup_type: Literal["THREE_STEP", "AGGRESSIVE_LEDGE"]
    lvn_id: str
    lvn_ref: Any
    ismt_or_smt_ref: Any
    signal_source: Optional[int]
    position_size_scale: float = 1.0


def enter_from_setup(setup: TradeSetup, aggressive_state: Optional[Any] = None) -> None:
    """
    Phase 5 commits an open here. For aggressive ledge, notify so D-14 suppression
    moves from pending → suppressed only after a real fill commit.
    """
    if setup.setup_type == "AGGRESSIVE_LEDGE":
        from src import entry as entry_mod

        st = aggressive_state or entry_mod.AggressiveLvnState()
        entry_mod.notify_aggressive_trade_completed(setup.lvn_id, st)
    raise NotImplementedError("Phase 5: full execution not implemented")
