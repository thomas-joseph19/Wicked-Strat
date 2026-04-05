"""RunWriter CSV append + D-14 HTML naming."""

import re
from pathlib import Path

import pytest

from src.config import make_run_paths
from src.position import ExitType, TradeResult
from src.reporting import RunWriter, chart_filename_d14


def _trade(idx: int) -> TradeResult:
    return TradeResult(
        setup_id=f"s{idx}",
        entry_price=100.0,
        stop_price=99.0,
        target_price=102.0,
        tp2_price=104.0,
        rr_ratio=1.0,
        direction="LONG",
        created_at=0,
        setup_type="THREE_STEP",
        lvn_id="1",
        exit_price_tp1=102.0,
        exit_price_tp2=None,
        exit_type=ExitType.PARTIAL_TP,
        gross_pnl=50.0,
        net_pnl=40.0,
        total_commission=10.0,
        trade_index=idx,
        session_date="2024-06-03",
        entry_bar_index=1,
        exit_bar_index=2,
        signal_source=None,
        position_size_scale=1.0,
    )


def test_append_trade_csv_header_then_row(tmp_path: Path):
    paths = make_run_paths(tmp_path, run_ts="20260102_120000")
    w = RunWriter(paths)
    w.append_trade_csv(_trade(0))
    w.append_trade_csv(_trade(1))
    text = paths.csv_path.read_text(encoding="utf-8")
    lines = text.strip().splitlines()
    assert len(lines) == 3
    assert "setup_id" in lines[0]
    assert "s0" in lines[1] and "s1" in lines[2]


def test_chart_filename_d14_pattern():
    name = chart_filename_d14(_trade(7))
    assert re.match(r"^0007_2024-06-03_LONG_THREE_STEP\.html$", name)


def test_write_trade_html_creates_file(tmp_path: Path):
    pytest.importorskip("plotly")
    import plotly.graph_objects as go

    paths = make_run_paths(tmp_path, run_ts="20260102_120000")
    w = RunWriter(paths)
    tr = _trade(3)
    fig = go.Figure()
    fig.add_bar(x=[1], y=[2])
    out = w.write_trade_html(tr, fig)
    assert out.exists()
    assert out.name == chart_filename_d14(tr)
