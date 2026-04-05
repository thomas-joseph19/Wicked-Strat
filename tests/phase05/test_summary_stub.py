"""summary.md after finalize_summary."""

from pathlib import Path

from src.config import make_run_paths
from src.position import ExitType, TradeResult
from src.reporting import RunWriter


def test_finalize_summary_net_total(tmp_path: Path):
    paths = make_run_paths(tmp_path, run_ts="20260102_120000")
    w = RunWriter(paths, instrument_symbol="NQ")
    w.append_trade_csv(
        TradeResult(
            setup_id="a",
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
            exit_price_tp2=103.0,
            exit_type=ExitType.PARTIAL_TP,
            gross_pnl=120.0,
            net_pnl=100.0,
            total_commission=20.0,
            trade_index=0,
            session_date="2024-06-03",
            entry_bar_index=1,
            exit_bar_index=3,
            signal_source=1,
            position_size_scale=1.0,
        )
    )
    w.append_trade_csv(
        TradeResult(
            setup_id="b",
            entry_price=200.0,
            stop_price=199.0,
            target_price=202.0,
            tp2_price=204.0,
            rr_ratio=1.0,
            direction="SHORT",
            created_at=1,
            setup_type="THREE_STEP",
            lvn_id="2",
            exit_price_tp1=None,
            exit_price_tp2=198.0,
            exit_type=ExitType.FULL_TP,
            gross_pnl=80.0,
            net_pnl=70.0,
            total_commission=10.0,
            trade_index=1,
            session_date="2024-06-03",
            entry_bar_index=2,
            exit_bar_index=5,
            signal_source=None,
            position_size_scale=1.0,
        )
    )
    out = w.finalize_summary()
    assert out.exists()
    body = out.read_text(encoding="utf-8")
    assert "Phase 5 stub" in body
    assert "2" in body
    assert "170.00" in body or "170" in body
    assert "backtest_results_20260102_120000.csv" in body
