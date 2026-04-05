"""
SMT: dual-instrument divergence with 20-bar Pearson correlation on simple returns.
Uses columns: close_nq, close_es, is_synthetic, is_synthetic_nq, is_synthetic_es (from data_loader).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Literal, Optional, Sequence

import numpy as np
import pandas as pd

from src.swings import SwingPoint


@dataclass
class SmtSignal:
    direction: Literal["LONG", "SHORT"]
    confirmed_at: int
    divergence_strength: float
    correlation_at_signal: float
    nq_swing: SwingPoint
    es_swing: SwingPoint
    signal_kind: Literal["SMT"] = "SMT"
    invalidated: bool = False


def _simple_returns(close: np.ndarray) -> np.ndarray:
    """Return r[k] = (c[k]-c[k-1])/c[k-1] for k>=1, length len(close)-1."""
    c = close.astype(float)
    prev = c[:-1]
    nxt = c[1:]
    with np.errstate(divide="ignore", invalid="ignore"):
        r = (nxt - prev) / np.where(prev != 0, prev, np.nan)
    return r


def pearson_corr_from_returns(r_nq: np.ndarray, r_es: np.ndarray) -> float:
    """Pearson correlation for two same-length return vectors (used in tests + SMT gate)."""
    if len(r_nq) != len(r_es) or len(r_nq) < 2:
        return float("nan")
    cmat = np.corrcoef(r_nq.astype(float), r_es.astype(float))
    if cmat.shape != (2, 2):
        return float("nan")
    return float(cmat[0, 1])


def pearson_corr_20_at_bar(close_nq: np.ndarray, close_es: np.ndarray, i: int) -> float:
    """
    20 simple returns ending at bar i: indices of returns correspond to bars i-19..i
    (return at end of bar k uses close[k] and close[k-1]). Requires i >= 19.
    """
    if i < 19 or i + 1 > len(close_nq) or len(close_es) != len(close_nq):
        return float("nan")
    # returns for bars k = i-19 .. i  => use closes from i-20 .. i
    sl_nq = close_nq[i - 20 : i + 1]
    sl_es = close_es[i - 20 : i + 1]
    r_nq = _simple_returns(sl_nq)
    r_es = _simple_returns(sl_es)
    if len(r_nq) != 20 or len(r_es) != 20:
        return float("nan")
    if np.any(~np.isfinite(r_nq)) or np.any(~np.isfinite(r_es)):
        return float("nan")
    cmat = np.corrcoef(r_nq, r_es)
    if cmat.shape != (2, 2):
        return float("nan")
    return float(cmat[0, 1])


def synthetic_count_in_window(stream: pd.DataFrame, i: int, win: int = 20) -> int:
    lo, hi = i - (win - 1), i
    if lo < 0:
        return 999
    col = "is_synthetic" if "is_synthetic" in stream.columns else None
    if col is None:
        return 0
    return int(stream.iloc[lo : hi + 1][col].sum())


def detect_smt_at_bar(
    stream: pd.DataFrame,
    i: int,
    nq_swings: Sequence[SwingPoint],
    es_swings: Sequence[SwingPoint],
    atr20_i: float,
    corr_min: float = 0.70,
) -> Optional[SmtSignal]:
    if i < 19 or atr20_i <= 0:
        return None

    row = stream.iloc[i]
    syn_nq = bool(row.get("is_synthetic_nq", False))
    syn_es = bool(row.get("is_synthetic_es", False))
    if syn_nq or syn_es:
        return None

    if synthetic_count_in_window(stream, i, 20) > 2:
        return None

    close_nq = stream["close_nq"].values
    close_es = stream["close_es"].values
    corr = pearson_corr_20_at_bar(close_nq, close_es, i)
    if not np.isfinite(corr) or corr < corr_min:
        return None

    nq_highs = [s for s in nq_swings if s.direction == "HIGH" and s.confirmed_at <= i]
    es_highs = [s for s in es_swings if s.direction == "HIGH" and s.confirmed_at <= i]
    nq_lows = [s for s in nq_swings if s.direction == "LOW" and s.confirmed_at <= i]
    es_lows = [s for s in es_swings if s.direction == "LOW" and s.confirmed_at <= i]

    # Bearish (SHORT): NQ HH vs ES LH
    if len(nq_highs) >= 2 and len(es_highs) >= 2:
        pnq, nnq = nq_highs[-2], nq_highs[-1]
        pes, nes = es_highs[-2], es_highs[-1]
        if abs(nnq.confirmed_at - nes.confirmed_at) <= 3:
            nq_move = nnq.price - pnq.price
            es_move = nes.price - pes.price
            if nq_move >= 0.3 * atr20_i and es_move <= 0.1 * atr20_i:
                div = (nq_move - es_move) / atr20_i
                ca = max(nnq.confirmed_at, nes.confirmed_at)
                return SmtSignal(
                    direction="SHORT",
                    confirmed_at=ca,
                    divergence_strength=div,
                    correlation_at_signal=corr,
                    nq_swing=nnq,
                    es_swing=nes,
                )

    # Bullish (LONG): NQ LL vs ES HL
    if len(nq_lows) >= 2 and len(es_lows) >= 2:
        pnq, nnq = nq_lows[-2], nq_lows[-1]
        pes, nes = es_lows[-2], es_lows[-1]
        if abs(nnq.confirmed_at - nes.confirmed_at) <= 3:
            nq_move = nnq.price - pnq.price
            es_move = nes.price - pes.price
            if nq_move <= -0.3 * atr20_i and es_move >= -0.1 * atr20_i:
                div = (es_move - nq_move) / atr20_i
                ca = max(nnq.confirmed_at, nes.confirmed_at)
                return SmtSignal(
                    direction="LONG",
                    confirmed_at=ca,
                    divergence_strength=div,
                    correlation_at_signal=corr,
                    nq_swing=nnq,
                    es_swing=nes,
                )

    return None
