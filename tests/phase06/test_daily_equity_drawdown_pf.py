"""METRIC-01, 04, 05, 06 — daily series, equity, drawdown, profit factor, stats."""

import pandas as pd
import pytest

from src.metrics import (
    basic_trade_stats,
    build_daily_pnl_and_returns,
    compounded_equity_from_returns,
    max_drawdown_stats,
    profit_factor,
)
from tests.phase06.conftest import make_trade


def test_daily_two_trades_same_day():
    t1 = make_trade(net_pnl=800.0)
    t2 = make_trade(net_pnl=-200.0, trade_index=1)
    df = build_daily_pnl_and_returns([t1, t2], account_size=100_000.0)
    assert len(df) == 1
    assert df.iloc[0]["daily_net_pnl"] == pytest.approx(600.0)
    assert df.iloc[0]["daily_return"] == pytest.approx(600.0 / 100_000.0)


def test_zero_pnl_dates_injected():
    t = make_trade(session_date="2024-06-03", net_pnl=100.0)
    df = build_daily_pnl_and_returns(
        [t], account_size=100_000.0, zero_pnl_dates=["2024-06-01", "2024-06-02"]
    )
    dates = sorted(df["date"].tolist())
    assert dates == ["2024-06-01", "2024-06-02", "2024-06-03"]
    z = df.set_index("date").loc["2024-06-01"]
    assert z["daily_net_pnl"] == 0.0
    assert z["daily_return"] == 0.0


def test_compounded_equity():
    r = pd.Series([0.01, -0.02, 0.03])
    eq = compounded_equity_from_returns(r, start_equity=100_000.0)
    assert eq.iloc[0] == pytest.approx(101_000.0)
    assert eq.iloc[1] == pytest.approx(101_000.0 * 0.98)
    assert eq.iloc[2] == pytest.approx(eq.iloc[1] * 1.03)


def test_max_drawdown_second_dip_deeper():
    # Running peak 110k then trough 88k => -20% from peak (deeper than interim -9.09%)
    equity = pd.Series([100_000.0, 110_000.0, 100_000.0, 110_000.0, 88_000.0])
    dd = max_drawdown_stats(equity)
    assert dd["max_drawdown_frac"] == pytest.approx(-22_000.0 / 110_000.0)
    assert dd["max_drawdown_dollars"] == pytest.approx(22_000.0)


def test_profit_factor_all_winners():
    trades = [make_trade(net_pnl=50.0, trade_index=i) for i in range(3)]
    assert profit_factor(trades) == pytest.approx(150.0)


def test_profit_factor_mixed():
    trades = [
        make_trade(net_pnl=100.0, trade_index=0),
        make_trade(net_pnl=-40.0, trade_index=1),
    ]
    assert profit_factor(trades) == pytest.approx(100.0 / 40.0)


def test_profit_factor_no_trades():
    assert profit_factor([]) == 0.0


def test_basic_trade_stats():
    trades = [
        make_trade(net_pnl=100.0, trade_index=0),
        make_trade(net_pnl=-50.0, trade_index=1),
        make_trade(net_pnl=0.0, trade_index=2),
    ]
    s = basic_trade_stats(trades)
    assert s["total_trades"] == 3
    assert s["win_rate"] == pytest.approx(1 / 3)
    assert s["avg_win"] == pytest.approx(100.0)
    assert s["avg_loss"] == pytest.approx(-50.0)
    assert s["total_net_pnl"] == pytest.approx(50.0)
