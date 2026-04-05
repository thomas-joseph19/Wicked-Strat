import pytest

from src.position import SessionTradeBudget, compute_position_size


def test_sizing_example_5_contracts():
    n = compute_position_size(
        entry=18000.0,
        stop=17990.0,
        account_size=100_000.0,
        risk_per_trade=0.01,
        point_value=20.0,
        position_size_scale=1.0,
    )
    assert n == 5


def test_sizing_scale_half():
    n = compute_position_size(
        entry=18000.0,
        stop=17990.0,
        account_size=100_000.0,
        risk_per_trade=0.01,
        point_value=20.0,
        position_size_scale=0.5,
    )
    assert n == 2


def test_sizing_zero_risk_distance():
    assert compute_position_size(100.0, 100.0, 100_000, 0.01, 20.0, 1.0) == 0


def test_session_budget_third_open():
    b = SessionTradeBudget(max_trades=3, opens_this_session=0)
    assert b.can_enter()
    b.on_open_full()
    b.on_open_full()
    b.on_open_full()
    assert not b.can_enter()
