"""ISMT-01/02/03 — D-01/D-02 anchoring and sweep filter."""

import pytest

from src.ismt import IsmtSignal, detect_ismt_at_bar
from tests.phase04.conftest import make_swing


def test_ismt_bearish_fires_bar_t_plus_1_when_close_back():
    t1, t = 5, 10
    sh1 = make_swing(bar_index=3, confirmed_at=t1, price=100.0, direction="HIGH")
    sh2 = make_swing(bar_index=8, confirmed_at=t, price=101.0, direction="HIGH")
    swings = [sh1, sh2]
    j = t + 1
    sig = detect_ismt_at_bar(j, close_nq=99.5, atr20_at_j=10.0, swings=swings)
    assert sig is not None
    assert sig.confirmed_at == j
    assert sig.direction == "SHORT"


def test_ismt_no_lookahead_window_uses_confirmed_at_not_bar_index():
    # SH2 extreme at bar 5 but confirmed only at 10 — early close-back must not count
    sh1 = make_swing(bar_index=2, confirmed_at=4, price=100.0, direction="HIGH")
    sh2 = make_swing(bar_index=5, confirmed_at=10, price=101.0, direction="HIGH")
    swings = [sh1, sh2]
    j = 6  # SH2.bar_index + 1, but j < SH2.confirmed_at + 1
    sig = detect_ismt_at_bar(j, close_nq=99.0, atr20_at_j=10.0, swings=swings)
    assert sig is None


def test_ismt_sweep_rejected_at_2x_atr20_boundary():
    sh1 = make_swing(bar_index=1, confirmed_at=5, price=100.0, direction="HIGH")
    sh2 = make_swing(bar_index=3, confirmed_at=8, price=102.0, direction="HIGH")
    swings = [sh1, sh2]
    t = 8
    j = t + 1
    atr = 1.0
    sweep = 2.0
    assert sweep >= 2.0 * atr - 1e-12
    sig_big = detect_ismt_at_bar(j, close_nq=99.0, atr20_at_j=atr, swings=swings)
    assert sig_big is None

    sh2_ok = make_swing(bar_index=3, confirmed_at=8, price=101.99, direction="HIGH")
    swings_ok = [sh1, sh2_ok]
    sig_ok = detect_ismt_at_bar(j, close_nq=99.0, atr20_at_j=atr, swings=swings_ok)
    assert sig_ok is not None
    assert sig_ok.sweep_size < 2.0 * atr


def test_ismt_confirmation_spacing_rejects_gt_10():
    sh1 = make_swing(bar_index=1, confirmed_at=5, price=100.0, direction="HIGH")
    sh2 = make_swing(bar_index=3, confirmed_at=16, price=101.0, direction="HIGH")
    swings = [sh1, sh2]
    j = 17
    sig = detect_ismt_at_bar(j, close_nq=99.0, atr20_at_j=10.0, swings=swings)
    assert sig is None


def test_ismt_signal_fields_populated():
    sh1 = make_swing(bar_index=1, confirmed_at=5, price=100.0, direction="HIGH")
    sh2 = make_swing(bar_index=3, confirmed_at=8, price=101.0, direction="HIGH")
    swings = [sh1, sh2]
    j = 9
    sig = detect_ismt_at_bar(j, close_nq=99.0, atr20_at_j=10.0, swings=swings)
    assert isinstance(sig, IsmtSignal)
    assert sig.signal_kind == "ISMT"
    assert sig.sweep_size == pytest.approx(1.0)
    assert sig.entry_zone == sh1.price
