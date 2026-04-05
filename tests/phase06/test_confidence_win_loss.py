"""confidence_win_loss: winner vs loser attribution aggregates."""

from src.confidence_win_loss import summarize_confidence_by_outcome
from src.position import ExitType, TradeResult


def _ca(**kwargs):
    base = {
        "total_score": 0.7,
        "threshold_at_entry": 0.6,
        "session_bias": "BULLISH",
        "direction": "LONG",
        "approach": "full",
        "had_trigger_close": True,
        "had_structural": True,
        "had_respected_sp": False,
        "had_aggressive_window": False,
        "contrib_lvn_valid": 0.1,
        "contrib_bias": 0.14,
        "contrib_approach": 0.24,
        "contrib_trigger_close": 0.16,
        "contrib_structural": 0.16,
        "contrib_respected_sp": 0.0,
        "contrib_aggressive_window": 0.0,
    }
    base.update(kwargs)
    return base


def test_summarize_splits_winners_losers():
    trades = [
        TradeResult(
            setup_id="w",
            entry_price=100.0,
            stop_price=99.0,
            target_price=102.0,
            tp2_price=104.0,
            rr_ratio=1.0,
            direction="LONG",
            created_at=0,
            setup_type="CONFIDENCE_SCORE",
            lvn_id="1",
            exit_price_tp1=None,
            exit_price_tp2=103.0,
            exit_type=ExitType.FULL_TP,
            gross_pnl=120.0,
            net_pnl=100.0,
            total_commission=20.0,
            trade_index=0,
            session_date="2024-01-02",
            entry_bar_index=1,
            exit_bar_index=2,
            signal_source=None,
            position_size_scale=1.0,
            confidence_attribution=_ca(contrib_structural=0.16),
        ),
        TradeResult(
            setup_id="l",
            entry_price=100.0,
            stop_price=99.0,
            target_price=102.0,
            tp2_price=104.0,
            rr_ratio=1.0,
            direction="LONG",
            created_at=0,
            setup_type="CONFIDENCE_SCORE",
            lvn_id="1",
            exit_price_tp1=None,
            exit_price_tp2=99.0,
            exit_type=ExitType.STOP,
            gross_pnl=-80.0,
            net_pnl=-100.0,
            total_commission=20.0,
            trade_index=1,
            session_date="2024-01-03",
            entry_bar_index=1,
            exit_bar_index=2,
            signal_source=None,
            position_size_scale=1.0,
            confidence_attribution=_ca(contrib_structural=0.0, had_structural=False),
        ),
    ]
    out = summarize_confidence_by_outcome(trades)
    assert out["confidence_score_trades_with_attribution"] == 2
    assert out["winners"]["count"] == 1
    assert out["losers"]["count"] == 1
    d = out["winner_minus_loser"]["mean_contributions"]
    assert d["contrib_structural"] == 0.16


def test_summarize_empty_without_attribution():
    t = TradeResult(
        setup_id="x",
        entry_price=100.0,
        stop_price=99.0,
        target_price=102.0,
        tp2_price=104.0,
        rr_ratio=1.0,
        direction="LONG",
        created_at=0,
        setup_type="THREE_STEP",
        lvn_id="1",
        exit_price_tp1=None,
        exit_price_tp2=103.0,
        exit_type=ExitType.FULL_TP,
        gross_pnl=100.0,
        net_pnl=90.0,
        total_commission=10.0,
        trade_index=0,
        session_date="2024-01-02",
        entry_bar_index=1,
        exit_bar_index=2,
        signal_source=1,
        position_size_scale=1.0,
    )
    out = summarize_confidence_by_outcome([t])
    assert out["confidence_score_trades_with_attribution"] == 0
