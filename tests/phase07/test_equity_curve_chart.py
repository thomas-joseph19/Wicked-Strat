"""Phase 7 D-05/D-06 equity curve HTML."""

from pathlib import Path

import pandas as pd

from src.plotting import build_equity_curve_figure, write_equity_curve_html


def test_equity_figure_structure():
    dates = ["2024-01-01", "2024-01-02", "2024-01-03"]
    eq = pd.Series([100_000.0, 101_000.0, 100_500.0])
    eps = [{"peak_date": "2024-01-01", "trough_date": "2024-01-03"}]
    fig = build_equity_curve_figure(dates, eq, start_equity=100_000.0, top_episodes=eps)
    types = [type(t).__name__ for t in fig.data]
    assert "Scatter" in types
    html = fig.to_html()
    assert len(html) > 500


def test_write_equity_curve_html(tmp_path: Path):
    fig = build_equity_curve_figure(["2024-06-01"], pd.Series([100_000.0]))
    out = write_equity_curve_html(tmp_path, "20260101_120000", fig)
    assert out.exists()
    assert out.stat().st_size > 500
    assert "equity_curve_20260101_120000.html" in str(out)
