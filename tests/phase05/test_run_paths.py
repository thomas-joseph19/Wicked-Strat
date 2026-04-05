from pathlib import Path

from src.config import make_run_paths


def test_run_paths_d14_segments(tmp_path):
    p = make_run_paths(tmp_path, run_ts="20260102_153045")
    assert p.run_timestamp == "20260102_153045"
    assert p.run_root == tmp_path / "run_20260102_153045"
    assert p.csv_path.name == "backtest_results_20260102_153045.csv"
    assert p.charts_dir.name == "charts_20260102_153045"
    assert "run_20260102_153045" in str(p.run_root)
