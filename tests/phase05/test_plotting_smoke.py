"""Smoke: Plotly figure builds and serializes."""

import numpy as np
import pandas as pd

from src.lvn import LVNZone
from src.plotting import build_trade_chart
from src.position import ExitType, TradeResult
from src.volume_profile import VolumeProfile


def _bars_with_volume() -> pd.DataFrame:
    rows = []
    for i in range(120):
        p = 100.0 + i * 0.02
        rows.append(
            {
                "open_nq": p,
                "high_nq": p + 0.5,
                "low_nq": p - 0.5,
                "close_nq": p + 0.1,
                "open_es": p,
                "high_es": p + 0.5,
                "low_es": p - 0.5,
                "close_es": p + 0.1,
                "volume_nq": 100.0,
            }
        )
    return pd.DataFrame(rows)


def test_build_trade_chart_has_candlestick_and_html():
    bars = _bars_with_volume()
    trade = TradeResult(
        setup_id="s1",
        entry_price=100.5,
        stop_price=99.0,
        target_price=102.0,
        tp2_price=104.0,
        rr_ratio=1.5,
        direction="LONG",
        created_at=0,
        setup_type="THREE_STEP",
        lvn_id="1",
        exit_price_tp1=102.0,
        exit_price_tp2=103.5,
        exit_type=ExitType.PARTIAL_TP,
        gross_pnl=100.0,
        net_pnl=90.0,
        total_commission=10.0,
        trade_index=0,
        session_date="2024-06-03",
        entry_bar_index=10,
        exit_bar_index=40,
        signal_source=1,
        position_size_scale=1.0,
    )
    lvn = LVNZone(
        low=100.0,
        high=101.0,
        midpoint=100.5,
        width_ticks=4,
        strength=0.5,
        session_id="t",
        valid=True,
    )
    base = float(bars["low_nq"].min()) - 50.0
    n = int(round((float(bars["high_nq"].max()) + 50.0 - base) / 0.25)) + 1
    vp = VolumeProfile("t", 0.25, base, np.zeros(n, dtype=np.float32))
    vp.volumes[vp.get_tick_idx(100.25)] = 500.0
    vp.compute_stats()

    fig = build_trade_chart(trade, bars, vp, lvn, instrument_symbol="NQ")
    types = [type(t).__name__ for t in fig.data]
    assert "Candlestick" in types
    html = fig.to_html()
    assert "plotly" in html.lower() or "candlestick" in html.lower()
