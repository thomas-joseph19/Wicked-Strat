"""
Weighted entry confidence (Phase 5.1+): partial confluence contributes to a score.
If score >= threshold, emit a TradeSetup (setup_type CONFIDENCE_SCORE).

Weights are static placeholders for later ML; tune via StrategyThresholds fields.
"""

from __future__ import annotations

from datetime import time
from typing import Any, List, Literal, Optional, Sequence

import pandas as pd

from src.config import StrategyThresholds
from src.entry import (
    approaches_lvn_long,
    approaches_lvn_short,
    build_trade_setup,
    get_structural_confirmation,
)
from src.ismt import IsmtSignal
from src.lvn import LVNZone
from src.position import ConfidenceAttribution, TradeSetup
from src.smt import SmtSignal


def _bar_time(bar: pd.Series) -> time:
    t = bar.name
    return t.time() if hasattr(t, "time") else time(9, 45)


def _hhmm_to_time(s: str) -> time:
    parts = str(s).strip().split(":")
    h = int(parts[0])
    m = int(parts[1]) if len(parts) > 1 else 0
    return time(h, m)


def _in_aggressive_window(bar: pd.Series, th: StrategyThresholds) -> bool:
    bt = _bar_time(bar)
    ag0 = _hhmm_to_time(th.aggressive_ledge_window_start)
    ag1 = _hhmm_to_time(th.aggressive_ledge_window_end)
    return ag0 <= bt <= ag1


def _touch_lvn_long(bar: pd.Series, lvn: LVNZone, tick_size: float) -> bool:
    buf = 3.0 * tick_size
    return float(bar["low_nq"]) <= float(lvn.high) + buf


def _touch_lvn_short(bar: pd.Series, lvn: LVNZone, tick_size: float) -> bool:
    buf = 3.0 * tick_size
    return float(bar["high_nq"]) >= float(lvn.low) - buf


def _prior_closes_above_lvn(prior: List[pd.Series], lvn: LVNZone, n: int) -> bool:
    if len(prior) < n:
        return False
    closes = [float(b["close_nq"]) for b in prior[-n:]]
    return all(c > float(lvn.high) for c in closes)


def _prior_closes_below_lvn(prior: List[pd.Series], lvn: LVNZone, n: int) -> bool:
    if len(prior) < n:
        return False
    closes = [float(b["close_nq"]) for b in prior[-n:]]
    return all(c < float(lvn.low) for c in closes)


def _bullish_trigger_long(bar: pd.Series, lvn: LVNZone) -> bool:
    c = float(bar["close_nq"])
    o = float(bar["open_nq"])
    return c > float(lvn.high) and c > o


def _bearish_trigger_short(bar: pd.Series, lvn: LVNZone) -> bool:
    c = float(bar["close_nq"])
    o = float(bar["open_nq"])
    return c < float(lvn.low) and c < o


def _sp_long_ok(sp_zones: Sequence[Any], entry_price: float) -> bool:
    return any(
        getattr(sp, "respected_overnight", False) and float(sp.low) > entry_price for sp in sp_zones
    )


def _sp_short_ok(sp_zones: Sequence[Any], entry_price: float) -> bool:
    return any(
        getattr(sp, "respected_overnight", False) and float(sp.high) < entry_price for sp in sp_zones
    )


def _zero_breakdown(
    bias_s: str, direction: Literal["LONG", "SHORT"], th: StrategyThresholds
) -> ConfidenceAttribution:
    z = 0.0
    return ConfidenceAttribution(
        total_score=0.0,
        threshold_at_entry=float(th.entry_confidence_threshold),
        session_bias=bias_s,
        direction=direction,
        approach="none",
        had_trigger_close=False,
        had_structural=False,
        had_respected_sp=False,
        had_aggressive_window=False,
        contrib_lvn_valid=z,
        contrib_bias=z,
        contrib_approach=z,
        contrib_trigger_close=z,
        contrib_structural=z,
        contrib_respected_sp=z,
        contrib_aggressive_window=z,
    )


def confidence_breakdown_long(
    i: int,
    bar: pd.Series,
    prior_bars: List[pd.Series],
    lvn: LVNZone,
    bias_s: str,
    sp_zones: Sequence[Any],
    ismt_signals: Sequence[IsmtSignal],
    smt_signals: Sequence[SmtSignal],
    tick_size: float,
    th: StrategyThresholds,
) -> ConfidenceAttribution:
    if lvn is None or not lvn.valid:
        return _zero_breakdown(bias_s, "LONG", th)
    w = th
    contrib_lvn = float(w.conf_weight_lvn_valid)
    contrib_bias = 0.0
    if bias_s == "BULLISH":
        contrib_bias = float(w.conf_weight_bias_aligned)
    elif bias_s == "NEUTRAL":
        contrib_bias = float(w.conf_weight_bias_neutral)
    n = max(1, int(w.approach_min_prior_closes))
    full_ap = approaches_lvn_long(bar, prior_bars, lvn, tick_size, min_prior_closes=n)
    approach = "none"
    contrib_ap = 0.0
    if full_ap:
        contrib_ap = float(w.conf_weight_approach_full)
        approach = "full"
    else:
        if _touch_lvn_long(bar, lvn, tick_size):
            contrib_ap = float(w.conf_weight_approach_touch_only)
            approach = "touch"
        elif _prior_closes_above_lvn(prior_bars, lvn, n):
            contrib_ap = float(w.conf_weight_approach_closes_only)
            approach = "closes"
    trig = _bullish_trigger_long(bar, lvn)
    contrib_trig = float(w.conf_weight_trigger_close) if trig else 0.0
    struct_ok = get_structural_confirmation("BULLISH", i, ismt_signals, smt_signals) is not None
    contrib_struct = float(w.conf_weight_structural) if struct_ok else 0.0
    ep = float(bar["close_nq"])
    sp_ok = _sp_long_ok(sp_zones, ep)
    contrib_sp = float(w.conf_weight_respected_sp) if sp_ok else 0.0
    ag_ok = _in_aggressive_window(bar, th)
    contrib_ag = float(w.conf_weight_aggressive_window_bonus) if ag_ok else 0.0
    s = contrib_lvn + contrib_bias + contrib_ap + contrib_trig + contrib_struct + contrib_sp + contrib_ag
    total = min(1.0, s)
    return ConfidenceAttribution(
        total_score=total,
        threshold_at_entry=float(th.entry_confidence_threshold),
        session_bias=bias_s,
        direction="LONG",
        approach=approach,
        had_trigger_close=trig,
        had_structural=struct_ok,
        had_respected_sp=sp_ok,
        had_aggressive_window=ag_ok,
        contrib_lvn_valid=contrib_lvn,
        contrib_bias=contrib_bias,
        contrib_approach=contrib_ap,
        contrib_trigger_close=contrib_trig,
        contrib_structural=contrib_struct,
        contrib_respected_sp=contrib_sp,
        contrib_aggressive_window=contrib_ag,
    )


def confidence_breakdown_short(
    i: int,
    bar: pd.Series,
    prior_bars: List[pd.Series],
    lvn: LVNZone,
    bias_s: str,
    sp_zones: Sequence[Any],
    ismt_signals: Sequence[IsmtSignal],
    smt_signals: Sequence[SmtSignal],
    tick_size: float,
    th: StrategyThresholds,
) -> ConfidenceAttribution:
    if lvn is None or not lvn.valid:
        return _zero_breakdown(bias_s, "SHORT", th)
    w = th
    contrib_lvn = float(w.conf_weight_lvn_valid)
    contrib_bias = 0.0
    if bias_s == "BEARISH":
        contrib_bias = float(w.conf_weight_bias_aligned)
    elif bias_s == "NEUTRAL":
        contrib_bias = float(w.conf_weight_bias_neutral)
    n = max(1, int(w.approach_min_prior_closes))
    full_ap = approaches_lvn_short(bar, prior_bars, lvn, tick_size, min_prior_closes=n)
    approach = "none"
    contrib_ap = 0.0
    if full_ap:
        contrib_ap = float(w.conf_weight_approach_full)
        approach = "full"
    else:
        if _touch_lvn_short(bar, lvn, tick_size):
            contrib_ap = float(w.conf_weight_approach_touch_only)
            approach = "touch"
        elif _prior_closes_below_lvn(prior_bars, lvn, n):
            contrib_ap = float(w.conf_weight_approach_closes_only)
            approach = "closes"
    trig = _bearish_trigger_short(bar, lvn)
    contrib_trig = float(w.conf_weight_trigger_close) if trig else 0.0
    struct_ok = get_structural_confirmation("BEARISH", i, ismt_signals, smt_signals) is not None
    contrib_struct = float(w.conf_weight_structural) if struct_ok else 0.0
    ep = float(bar["close_nq"])
    sp_ok = _sp_short_ok(sp_zones, ep)
    contrib_sp = float(w.conf_weight_respected_sp) if sp_ok else 0.0
    ag_ok = _in_aggressive_window(bar, th)
    contrib_ag = float(w.conf_weight_aggressive_window_bonus) if ag_ok else 0.0
    s = contrib_lvn + contrib_bias + contrib_ap + contrib_trig + contrib_struct + contrib_sp + contrib_ag
    total = min(1.0, s)
    return ConfidenceAttribution(
        total_score=total,
        threshold_at_entry=float(th.entry_confidence_threshold),
        session_bias=bias_s,
        direction="SHORT",
        approach=approach,
        had_trigger_close=trig,
        had_structural=struct_ok,
        had_respected_sp=sp_ok,
        had_aggressive_window=ag_ok,
        contrib_lvn_valid=contrib_lvn,
        contrib_bias=contrib_bias,
        contrib_approach=contrib_ap,
        contrib_trigger_close=contrib_trig,
        contrib_structural=contrib_struct,
        contrib_respected_sp=contrib_sp,
        contrib_aggressive_window=contrib_ag,
    )


def entry_confidence_long(
    i: int,
    bar: pd.Series,
    prior_bars: List[pd.Series],
    lvn: LVNZone,
    bias_s: str,
    sp_zones: Sequence[Any],
    ismt_signals: Sequence[IsmtSignal],
    smt_signals: Sequence[SmtSignal],
    tick_size: float,
    th: StrategyThresholds,
) -> float:
    return confidence_breakdown_long(
        i, bar, prior_bars, lvn, bias_s, sp_zones, ismt_signals, smt_signals, tick_size, th
    ).total_score


def entry_confidence_short(
    i: int,
    bar: pd.Series,
    prior_bars: List[pd.Series],
    lvn: LVNZone,
    bias_s: str,
    sp_zones: Sequence[Any],
    ismt_signals: Sequence[IsmtSignal],
    smt_signals: Sequence[SmtSignal],
    tick_size: float,
    th: StrategyThresholds,
) -> float:
    return confidence_breakdown_short(
        i, bar, prior_bars, lvn, bias_s, sp_zones, ismt_signals, smt_signals, tick_size, th
    ).total_score


def evaluate_confidence_long(
    i: int,
    bar: pd.Series,
    prior_bars: List[pd.Series],
    lvn: LVNZone,
    bias_s: str,
    sp_zones: Sequence[Any],
    ismt_signals: Sequence[IsmtSignal],
    smt_signals: Sequence[SmtSignal],
    atr5: float,
    atr20: float,
    tick_size: float,
    th: StrategyThresholds,
) -> Optional[TradeSetup]:
    attr = confidence_breakdown_long(
        i, bar, prior_bars, lvn, bias_s, sp_zones, ismt_signals, smt_signals, tick_size, th
    )
    if attr.total_score < float(th.entry_confidence_threshold):
        return None
    struct = get_structural_confirmation("BULLISH", i, ismt_signals, smt_signals)
    return build_trade_setup(
        bar_index=i,
        bar=bar,
        direction="LONG",
        setup_type="CONFIDENCE_SCORE",
        lvn=lvn,
        structural=struct,
        atr5=atr5,
        atr20=atr20,
        sp_zones=sp_zones,
        tick_size=tick_size,
        confidence_attribution=attr.to_dict(),
    )


def evaluate_confidence_short(
    i: int,
    bar: pd.Series,
    prior_bars: List[pd.Series],
    lvn: LVNZone,
    bias_s: str,
    sp_zones: Sequence[Any],
    ismt_signals: Sequence[IsmtSignal],
    smt_signals: Sequence[SmtSignal],
    atr5: float,
    atr20: float,
    tick_size: float,
    th: StrategyThresholds,
) -> Optional[TradeSetup]:
    attr = confidence_breakdown_short(
        i, bar, prior_bars, lvn, bias_s, sp_zones, ismt_signals, smt_signals, tick_size, th
    )
    if attr.total_score < float(th.entry_confidence_threshold):
        return None
    struct = get_structural_confirmation("BEARISH", i, ismt_signals, smt_signals)
    return build_trade_setup(
        bar_index=i,
        bar=bar,
        direction="SHORT",
        setup_type="CONFIDENCE_SCORE",
        lvn=lvn,
        structural=struct,
        atr5=atr5,
        atr20=atr20,
        sp_zones=sp_zones,
        tick_size=tick_size,
        confidence_attribution=attr.to_dict(),
    )
