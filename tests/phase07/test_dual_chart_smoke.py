"""Phase 7 dual NQ+ES charts."""

import numpy as np
import pandas as pd

from src.lvn import LVNZone
from src.plotting import TradeChartContext, build_trade_chart_dual
from src.position import ExitType, TradeResult
from src.volume_profile import VolumeProfile


def _trade() -> TradeResult:
    return TradeResult(
        setup_id="t",
        entry_price=100.0,
        stop_price=99.0,
        target_price=101.0,
        tp2_price=102.0,
        rr_ratio=1.0,
        direction="LONG",
        created_at=0,
        setup_type="THREE_STEP",
        lvn_id="1",
        exit_price_tp1=None,
        exit_price_tp2=None,
        exit_type=ExitType.FULL_TP,
        gross_pnl=0.0,
        net_pnl=0.0,
        total_commission=0.0,
        trade_index=0,
        session_date="2024-06-03",
        entry_bar_index=5,
        exit_bar_index=10,
    )


def _bars(n: int = 30) -> pd.DataFrame:
    rows = []
    for i in range(n):
        p = 100.0 + i * 0.05
        rows.append(
            {
                "open_nq": p,
                "high_nq": p + 0.5,
                "low_nq": p - 0.25,
                "close_nq": p + 0.1,
                "open_es": p - 10,
                "high_es": p - 9.5,
                "low_es": p - 10.25,
                "close_es": p - 9.9,
            }
        )
    return pd.DataFrame(rows)


def _vp() -> VolumeProfile:
    base = 99.0
    arr = np.zeros(40, dtype=np.float32)
    arr[10] = 100.0
    vp = VolumeProfile("s", 0.25, base, arr)
    vp.compute_stats()
    return vp


def test_dual_chart_html():
    lvn = LVNZone(99.5, 100.5, 100.0, 4, 0.5, "s", True)
    fig = build_trade_chart_dual(_trade(), _bars(), _vp(), lvn)
    assert len(fig.data) >= 2
    html = fig.to_html()
    assert "ES" in html or "es" in html.lower()


def test_dual_overlays_bias_sp():
    class Z:
        low = 100.2
        high = 100.8

    ctx = TradeChartContext(bias="BULLISH", sp_zones=[Z()])
    lvn = LVNZone(99.0, 101.0, 100.0, 4, 0.5, "s", True)
    fig = build_trade_chart_dual(_trade(), _bars(), _vp(), lvn, chart_ctx=ctx)
    title = fig.layout.title.text if fig.layout.title else ""
    assert "BIAS" in str(title)
    assert len(fig.to_html()) > 400


def test_backtest_use_dual_charts(tmp_path, nq_instrument, thresholds):
    from dataclasses import replace

    from src.backtest import run_session_backtest
    from src.config import make_run_paths
    from tests.phase05.conftest import make_lvn, simple_setup

    paths = make_run_paths(tmp_path, run_ts="20260103_120000")
    lvn = make_lvn(50.0, 55.0)
    st = replace(
        simple_setup(entry=100.0, stop=98.0, tp1=101.5, tp2=103.0, created_at=0),
        lvn_ref=lvn,
    )
    rows = []
    for i in range(80):
        p = 100.0 + i * 0.1
        rows.append(
            {
                "open_nq": p,
                "high_nq": p + 1.0,
                "low_nq": p - 0.5,
                "close_nq": p + 0.2,
                "open_es": p - 10,
                "high_es": p - 9.0,
                "low_es": p - 10.5,
                "close_es": p - 9.2,
                "volume_nq": 50.0,
            }
        )
    bars = pd.DataFrame(rows)
    run_session_backtest(
        bars_df=bars,
        setups=[st],
        instrument=nq_instrument,
        thresholds=thresholds,
        paths=paths,
        session_date="2024-06-03",
        use_dual_charts=True,
    )
    html = list(paths.charts_dir.glob("*.html"))
    assert html
    assert "ES" in html[0].read_text(encoding="utf-8")
