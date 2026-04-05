from dataclasses import replace

import pytest

from src.position import (
    FillEvent,
    TradeSetup,
    fills_to_gross_pnl,
    total_commission_from_fills,
)
from tests.phase05.conftest import make_lvn


def _setup_long() -> TradeSetup:
    return TradeSetup(
        setup_id="x",
        entry_price=18000.0,
        stop_price=17900.0,
        target_price=18100.0,
        tp2_price=18200.0,
        rr_ratio=1.0,
        direction="LONG",
        created_at=0,
        setup_type="THREE_STEP",
        lvn_id="1",
        lvn_ref=make_lvn(17950.0, 17980.0),
        ismt_or_smt_ref=None,
        signal_source=1,
        position_size_scale=1.0,
    )


def _setup_short() -> TradeSetup:
    return replace(_setup_long(), direction="SHORT")


def test_short_gross_profit_when_price_falls():
    s = _setup_short()
    fills = [
        FillEvent(1, "ENTRY", 18000.0, 1, "SHORT"),
        FillEvent(2, "TP2", 17950.0, 1, "SHORT"),
    ]
    g = fills_to_gross_pnl(fills, s, point_value=20.0)
    assert g == pytest.approx((18000 - 17950) * 1 * 20)


def test_long_gross_loss_when_price_falls():
    s = _setup_long()
    fills = [
        FillEvent(1, "ENTRY", 18000.0, 1, "LONG"),
        FillEvent(2, "SL", 17950.0, 1, "LONG"),
    ]
    g = fills_to_gross_pnl(fills, s, point_value=20.0)
    assert g == pytest.approx((17950 - 18000) * 1 * 20)


def test_commission_partial_three_events():
    fills = [
        FillEvent(1, "ENTRY", 100.0, 5, "LONG"),
        FillEvent(2, "TP1_PARTIAL", 102.0, 3, "LONG"),
        FillEvent(3, "TP2", 104.0, 2, "LONG"),
    ]
    c = total_commission_from_fills(fills, commission_per_side=2.5)
    assert c == pytest.approx((5 + 3 + 2) * 2.5)
