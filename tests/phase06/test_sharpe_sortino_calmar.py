"""METRIC-02, 03 — Sharpe, Sortino, Calmar, recovery, annual."""

import math

import pandas as pd
import pytest

from src.metrics import (
    annual_breakdown,
    build_daily_pnl_and_returns,
    calmar_ratio,
    recovery_factor,
    sharpe_ratio_annualized,
    sortino_ratio_annualized,
)
from tests.phase06.conftest import make_trade


def test_sharpe_golden():
    r = pd.Series([0.001, -0.002, 0.003, 0.0, 0.001])
    mu = float(r.mean())
    sig = float(r.std(ddof=1))
    expected = (mu / sig) * math.sqrt(252)
    assert sharpe_ratio_annualized(r) == pytest.approx(expected)
    assert sharpe_ratio_annualized(pd.Series([0.01, 0.01])) is None  # std 0
    assert sharpe_ratio_annualized(pd.Series([0.01])) is None


def test_sortino_with_downside():
    r = pd.Series([0.01, -0.02, 0.01, -0.01, 0.0])
    downside = r[r < 0]
    dv = float((downside**2).mean())
    ddev_d = math.sqrt(dv)
    denom = ddev_d * math.sqrt(252)
    numer = float(r.mean()) * 252
    expected = numer / denom
    s, empty = sortino_ratio_annualized(r)
    assert empty is False
    assert s == pytest.approx(expected)


def test_sortino_no_downside():
    r = pd.Series([0.01, 0.02, 0.0])
    s, empty = sortino_ratio_annualized(r)
    assert s is None
    assert empty is True


def test_calmar():
    c = calmar_ratio(total_return_frac=0.21, num_years=1.0, max_drawdown_frac=-0.10)
    ann = 0.21
    assert c == pytest.approx(ann / 0.10)


def test_recovery_factor():
    assert recovery_factor(50_000.0, -25_000.0) == pytest.approx(2.0)
    assert recovery_factor(1.0, 0.0) == 0.0


def test_annual_breakdown():
    t1 = make_trade(session_date="2023-06-01", net_pnl=100.0)
    t2 = make_trade(session_date="2024-06-01", net_pnl=-50.0)
    df = build_daily_pnl_and_returns([t1, t2], 100_000.0)
    ab = annual_breakdown(df)
    assert set(ab["year"].tolist()) == {2023, 2024}
    y2023 = ab[ab["year"] == 2023].iloc[0]
    assert y2023["net_pnl"] == pytest.approx(100.0)
