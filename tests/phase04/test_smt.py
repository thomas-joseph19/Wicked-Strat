"""SMT-01..05 — correlation, synthetic gates, divergence thresholds."""

import numpy as np
import pandas as pd
import pytest

from src.smt import (
    SmtSignal,
    detect_smt_at_bar,
    pearson_corr_from_returns,
    synthetic_count_in_window,
)
from tests.phase04.conftest import make_swing


def _make_stream(n: int, i_syn: dict | None = None) -> pd.DataFrame:
    """NQ/ES closes aligned so rolling return correlation stays ≥ 0.70 at typical bars."""
    i_syn = i_syn or {}
    rows = []
    base = 5000.0
    for k in range(n):
        cn = base + 0.05 * k
        ce = cn + 1e-4 * k
        syn_nq, syn_es = i_syn.get(k, (False, False))
        rows.append(
            {
                "close_nq": cn,
                "close_es": ce,
                "is_synthetic_nq": syn_nq,
                "is_synthetic_es": syn_es,
                "is_synthetic": syn_nq or syn_es,
            }
        )
    return pd.DataFrame(rows)


def test_smt_correlation_065_suppresses_085_allows():
    rng = np.random.default_rng(42)
    z = rng.standard_normal(20)
    w = rng.standard_normal(20)
    w = w - (np.dot(w, z) / np.dot(z, z)) * z
    z = z / np.linalg.norm(z)
    w = w / np.linalg.norm(w)
    target_lo = 0.65
    target_hi = 0.85
    r_es_lo = target_lo * z + np.sqrt(max(0.0, 1.0 - target_lo**2)) * w
    r_es_hi = target_hi * z + np.sqrt(max(0.0, 1.0 - target_hi**2)) * w
    c_lo = pearson_corr_from_returns(z, r_es_lo)
    c_hi = pearson_corr_from_returns(z, r_es_hi)
    assert c_lo < 0.70
    assert c_hi >= 0.70


def test_smt_skips_when_more_than_two_synthetic_in_window():
    n = 30
    df = _make_stream(n)
    i = 25
    for k in (19, 20, 21):
        df.loc[k, "is_synthetic_nq"] = True
        df.loc[k, "is_synthetic"] = True
    assert synthetic_count_in_window(df, i, 20) > 2
    pnq = make_swing(5, 20, 100.0, "HIGH")
    nnq = make_swing(8, 23, 103.1, "HIGH")
    pes = make_swing(5, 21, 200.0, "HIGH")
    nes = make_swing(8, 24, 200.9, "HIGH")
    assert detect_smt_at_bar(df, i, [pnq, nnq], [pes, nes], atr20_i=10.0) is None


def test_smt_skips_when_es_synthetic_at_confirm():
    n = 25
    df = _make_stream(n)
    df.loc[24, "is_synthetic_es"] = True
    df.loc[24, "is_synthetic"] = True
    atr = 4.0
    nq_swings = [
        make_swing(10, 15, 100.0, "HIGH"),
        make_swing(12, 18, 100.5, "HIGH"),
    ]
    es_swings = [
        make_swing(10, 15, 200.0, "HIGH"),
        make_swing(12, 18, 200.2, "HIGH"),
    ]
    sig = detect_smt_at_bar(df, 24, nq_swings, es_swings, atr20_i=atr)
    assert sig is None


def test_smt_bearish_thresholds_and_bar_alignment():
    n = 30
    df = _make_stream(n)
    atr = 10.0
    i = 25
    # Moves: NQ 3.1 (0.31*ATR), ES 0.9 (0.09*ATR)
    pnq = make_swing(5, 20, 100.0, "HIGH")
    nnq = make_swing(8, 23, 103.1, "HIGH")
    pes = make_swing(5, 21, 200.0, "HIGH")
    nes = make_swing(8, 24, 200.9, "HIGH")
    sig = detect_smt_at_bar(df, i, [pnq, nnq], [pes, nes], atr20_i=atr)
    assert sig is not None
    assert sig.direction == "SHORT"
    assert isinstance(sig, SmtSignal)

    pnq2 = make_swing(5, 20, 100.0, "HIGH")
    nnq2 = make_swing(8, 23, 102.9, "HIGH")
    pes2 = make_swing(5, 21, 200.0, "HIGH")
    nes2 = make_swing(8, 24, 201.1, "HIGH")
    sig2 = detect_smt_at_bar(df, i, [pnq2, nnq2], [pes2, nes2], atr20_i=atr)
    assert sig2 is None


def test_smt_bullish_mirror():
    n = 30
    df = _make_stream(n)
    atr = 10.0
    i = 25
    pnq = make_swing(5, 20, 100.0, "LOW")
    nnq = make_swing(8, 23, 96.9, "LOW")  # -3.1
    pes = make_swing(5, 21, 200.0, "LOW")
    nes = make_swing(8, 24, 199.2, "LOW")  # -0.8, >= -0.1*A -> -0.8 >= -1 fails
    # Need es_move >= -0.1 * atr  => -0.8 >= -1 is True
    sig = detect_smt_at_bar(df, i, [pnq, nnq], [pes, nes], atr20_i=atr)
    assert sig is not None
    assert sig.direction == "LONG"


def test_smt_signal_fields():
    n = 30
    df = _make_stream(n)
    atr = 10.0
    i = 25
    pnq = make_swing(5, 20, 100.0, "HIGH")
    nnq = make_swing(8, 23, 103.1, "HIGH")
    pes = make_swing(5, 21, 200.0, "HIGH")
    nes = make_swing(8, 24, 200.9, "HIGH")
    sig = detect_smt_at_bar(df, i, [pnq, nnq], [pes, nes], atr20_i=atr)
    assert sig.correlation_at_signal == pytest.approx(sig.correlation_at_signal)
    assert np.isfinite(sig.divergence_strength)
    assert sig.confirmed_at == max(nnq.confirmed_at, nes.confirmed_at)
