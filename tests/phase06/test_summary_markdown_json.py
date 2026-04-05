"""summary_report: episodes, JSON, markdown sections, write API."""

import json
from pathlib import Path

import pandas as pd
import pytest

from src.metrics import list_drawdown_episodes
from src.position import ExitType
from src.summary_report import (
    KNOWN_MARKET_EVENTS,
    build_summary_dict,
    build_summary_markdown,
    write_run_summaries,
)
from tests.phase06.conftest import make_trade


def test_list_drawdown_episodes_synthetic():
    dates = ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]
    equity = pd.Series([100_000.0, 120_000.0, 100_000.0, 120_000.0, 85_000.0])
    eps = list_drawdown_episodes(dates, equity, min_depth_frac=0.05, max_rows=10)
    assert len(eps) >= 1
    deepest = eps[0]
    assert deepest["depth_frac"] < -0.1
    assert deepest["recovery_date"] is None or deepest["recovery_date"] is not None


def test_known_market_events_nonempty():
    assert len(KNOWN_MARKET_EVENTS) >= 2


def _minimal_payload():
    t = make_trade()
    daily = pd.DataFrame(
        [
            {"date": "2024-06-03", "daily_net_pnl": 100.0, "daily_return": 0.001},
        ]
    )
    return build_summary_dict(
        trades=[t],
        daily_df=daily,
        equity_stats={"max_drawdown_frac": 0.0, "max_drawdown_dollars": 0.0},
        risk_stats={
            "sharpe": 1.5,
            "sortino": 2.0,
            "sortino_downside_empty": False,
            "calmar": 0.5,
            "max_drawdown_frac": -0.05,
            "max_drawdown_dollars": 5000.0,
            "recovery_factor": 1.2,
            "total_return_frac": 0.01,
            "cagr_approx": 0.01,
        },
        trade_stats_extra={"total_trades": 1, "win_rate": 1.0, "avg_win": 100, "avg_loss": 0, "total_net_pnl": 100, "profit_factor": 100},
        daily_distribution={"trading_days": 1, "days_with_trades": 1, "std_daily_return": 0.0, "skewness": 0.0, "kurtosis": 0.0, "best_day_pnl": 100, "worst_day_pnl": 100},
        annual_df=pd.DataFrame([{"year": 2024, "net_pnl": 100.0, "sharpe": 1.0}]),
        drawdown_episodes=[
            {
                "peak_date": "2024-01-01",
                "trough_date": "2024-01-02",
                "recovery_date": "2024-01-03",
                "depth_frac": -0.08,
                "depth_dollars": 8000.0,
                "duration_calendar_days": 2,
            }
        ],
        session_diag={},
        run_meta={"run_timestamp": "t", "instrument": "NQ", "config_path": "c.yaml", "trade_count": 1},
        config_yaml_text="nq:\n  symbol: NQ\n",
        warnings=[],
    )


def test_build_summary_dict_json_roundtrip():
    p = _minimal_payload()
    s = json.dumps(p, default=str)
    assert "meta" in s
    assert "risk_adjusted" in s
    json.loads(s)


def test_build_summary_markdown_headings_order():
    md = build_summary_markdown(_minimal_payload())
    order = [
        "Executive Summary",
        "Risk-Adjusted Performance",
        "Trade Statistics",
        "Confidence vs outcome (entry score)",
        "Daily P&L Distribution",
        "Annual Breakdown",
        "Drawdown Analysis",
        "Session & Setup Quality",
        "Parameter Snapshot",
        "Notes & Warnings",
    ]
    positions = [md.find(x) for x in order]
    assert all(p >= 0 for p in positions)
    assert positions == sorted(positions)
    assert "```yaml" in md
    assert "nq:" in md


def test_scratch_count_in_payload():
    scratch = make_trade(net_pnl=1e-7, exit_type=ExitType.PARTIAL_TP)
    p = build_summary_dict(
        trades=[scratch],
        daily_df=pd.DataFrame([{"date": "2024-06-03", "daily_net_pnl": 1e-7, "daily_return": 1e-12}]),
        equity_stats={},
        risk_stats={"sharpe": None, "sortino": None, "sortino_downside_empty": True, "calmar": None, "max_drawdown_frac": 0.0, "max_drawdown_dollars": 0.0, "recovery_factor": 0.0, "total_return_frac": 0.0, "cagr_approx": 0.0},
        trade_stats_extra={"total_trades": 1, "win_rate": 0, "avg_win": 0, "avg_loss": 0, "total_net_pnl": 1e-7, "profit_factor": 0},
        daily_distribution={},
        annual_df=pd.DataFrame(),
        drawdown_episodes=[],
        session_diag={},
        run_meta={"run_timestamp": "t", "instrument": "NQ", "config_path": "x", "trade_count": 1},
        config_yaml_text="a: 1\n",
        warnings=[],
    )
    assert p["trade_stats"]["scratch_trades"] == 1


def test_write_run_summaries(tmp_path: Path):
    root = tmp_path / "run"
    md_path, js_path = write_run_summaries(root, "# heading\n\nparagraph text.\n", {"a": 1, "b": 2})
    assert md_path.exists() and js_path.exists()
    assert md_path.stat().st_size > 10
    assert js_path.stat().st_size > 10
    assert json.loads(js_path.read_text(encoding="utf-8")) == {"a": 1, "b": 2}
