"""compute_and_write_institutional_summaries + backtest flag."""

from pathlib import Path

import pandas as pd
import pytest

from src.config import make_run_paths
from src.metrics import compute_and_write_institutional_summaries
from tests.phase05.conftest import make_lvn, simple_setup
from tests.phase06.conftest import make_trade


def test_compute_and_write_creates_large_summaries(tmp_path: Path):
    paths = make_run_paths(tmp_path, run_ts="20260101_120000")
    paths.run_root.mkdir(parents=True, exist_ok=True)
    trades = [make_trade(net_pnl=250.0)]
    compute_and_write_institutional_summaries(
        trades=trades,
        paths=paths,
        account_size=100_000.0,
        config_yaml_text="thresholds:\n  account_size: 100000\n",
        instrument_symbol="NQ",
        run_timestamp=paths.run_timestamp,
    )
    md = paths.run_root / "summary.md"
    js = paths.run_root / "summary.json"
    dash = paths.run_root / f"metrics_dashboard_{paths.run_timestamp}.html"
    assert md.stat().st_size > 100
    assert js.stat().st_size > 100
    assert dash.is_file()
    assert dash.stat().st_size > 5000


def test_run_session_backtest_write_institutional_summaries(tmp_path: Path, nq_instrument, thresholds):
    from src.backtest import run_session_backtest

    paths = make_run_paths(tmp_path, run_ts="20260102_120000")
    lvn = make_lvn(50.0, 55.0)
    st = simple_setup(created_at=0)
    from dataclasses import replace

    st = replace(st, lvn_ref=lvn, tp2_price=103.0, target_price=101.5)
    rows = []
    for i in range(80):
        p = 100.0 + i * 0.1
        rows.append(
            {
                "open_nq": p,
                "high_nq": p + 1.0,
                "low_nq": p - 0.5,
                "close_nq": p + 0.2,
                "open_es": p,
                "high_es": p + 1.0,
                "low_es": p - 0.5,
                "close_es": p + 0.2,
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
        write_institutional_summaries=True,
        config_path=str(tmp_path / "nonexistent_config.yaml"),
    )
    assert (paths.run_root / "summary.md").exists()
    assert (paths.run_root / f"metrics_dashboard_{paths.run_timestamp}.html").exists()
    text = (paths.run_root / "summary.md").read_text(encoding="utf-8")
    assert "Executive Summary" in text
    assert "config.yaml not found" in text
