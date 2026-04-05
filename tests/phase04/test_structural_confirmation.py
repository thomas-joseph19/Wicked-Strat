"""SIG-01..03 — D-04/D-05/D-06 selector (REQ ISMT-first superseded)."""

from src.entry import get_structural_confirmation, signal_source_value
from src.ismt import IsmtSignal
from src.smt import SmtSignal
from tests.phase04.conftest import make_swing


def _ismt(ca: int, inv: bool = False) -> IsmtSignal:
    s1 = make_swing(0, ca - 2, 100.0, "LOW")
    s2 = make_swing(0, ca - 1, 99.0, "LOW")
    return IsmtSignal(
        direction="LONG",
        confirmed_at=ca,
        sweep_size=1.0,
        entry_zone=100.0,
        source_swings=(s1, s2),
        invalidated=inv,
    )


def _smt(ca: int) -> SmtSignal:
    nq = make_swing(0, ca, 100.0, "HIGH")
    es = make_swing(0, ca, 200.0, "HIGH")
    return SmtSignal(
        direction="LONG",
        confirmed_at=ca,
        divergence_strength=0.5,
        correlation_at_signal=0.9,
        nq_swing=nq,
        es_swing=es,
        swing_alignment_bar=ca,
    )


def test_sig_equal_priority_smt_wins_when_more_recent():
    ismt = _ismt(244)
    smt = _smt(245)
    picked = get_structural_confirmation("BULLISH", 247, [ismt], [smt])
    assert picked is smt
    assert signal_source_value(smt) == 0


def test_sig_rejects_confirmed_at_i_minus_6():
    ismt = _ismt(240)
    assert get_structural_confirmation("BULLISH", 245, [ismt], []) is None


def test_sig_drops_invalidated():
    bad = _ismt(250, inv=True)
    good = _ismt(248)
    picked = get_structural_confirmation("BULLISH", 251, [bad, good], [])
    assert picked is good


def test_sig_tiebreak_prefers_ismt():
    ismt = _ismt(250)
    smt = _smt(250)
    picked = get_structural_confirmation("BULLISH", 252, [ismt], [smt])
    assert picked is ismt


def test_sig_filters_by_direction():
    s_short = IsmtSignal(
        direction="SHORT",
        confirmed_at=250,
        sweep_size=1.0,
        entry_zone=100.0,
        source_swings=(make_swing(0, 248, 100.0, "HIGH"), make_swing(0, 249, 101.0, "HIGH")),
    )
    assert get_structural_confirmation("BULLISH", 252, [s_short], []) is None


def test_sig_signal_source_ismt_is_1():
    ismt = _ismt(250)
    assert signal_source_value(ismt) == 1


def test_sig_req_sig02_superseded_by_context_d04():
    """Document: recency beats naive REQ SIG-02 ISMT-first."""
    test_sig_equal_priority_smt_wins_when_more_recent()
