"""
Compare confidence attributions for winning vs losing CONFIDENCE_SCORE trades.

Use summary.json / institutional summary section to tune static weights in config.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Sequence

from src.position import TradeResult

CONTRIB_KEYS = (
    "contrib_lvn_valid",
    "contrib_bias",
    "contrib_approach",
    "contrib_trigger_close",
    "contrib_structural",
    "contrib_respected_sp",
    "contrib_aggressive_window",
)
BOOL_KEYS = (
    "had_trigger_close",
    "had_structural",
    "had_respected_sp",
    "had_aggressive_window",
)


def summarize_confidence_by_outcome(trades: Sequence[TradeResult]) -> Dict[str, Any]:
    scored = [
        t
        for t in trades
        if t.setup_type == "CONFIDENCE_SCORE" and t.confidence_attribution
    ]
    if not scored:
        return {
            "confidence_score_trades_with_attribution": 0,
            "note": "No CONFIDENCE_SCORE trades or confidence_attribution missing on results.",
        }

    wins = [t for t in scored if t.net_pnl > 0]
    losses = [t for t in scored if t.net_pnl < 0]
    flat = [t for t in scored if t.net_pnl == 0]

    def _side_dict(side: List[TradeResult]) -> Dict[str, Any]:
        if not side:
            return {"count": 0}
        scores = [float(t.confidence_attribution["total_score"]) for t in side]  # type: ignore[index]
        out: Dict[str, Any] = {
            "count": len(side),
            "mean_total_score": sum(scores) / len(scores),
            "mean_contributions": {
                k: sum(float(t.confidence_attribution[k]) for t in side) / len(side)  # type: ignore[index]
                for k in CONTRIB_KEYS
            },
            "share_with_flag": {
                k: sum(1 for t in side if t.confidence_attribution.get(k)) / len(side)  # type: ignore[union-attr]
                for k in BOOL_KEYS
            },
        }
        approaches = [str(t.confidence_attribution.get("approach", "none")) for t in side]  # type: ignore[union-attr]
        out["approach_counts"] = dict(Counter(approaches))
        biases = [str(t.confidence_attribution.get("session_bias", "")) for t in side]  # type: ignore[union-attr]
        out["session_bias_counts"] = dict(Counter(biases))
        dirs = [str(t.confidence_attribution.get("direction", "")) for t in side]  # type: ignore[union-attr]
        out["direction_counts"] = dict(Counter(dirs))
        return out

    w = _side_dict(wins)
    l_ = _side_dict(losses)
    f = _side_dict(flat)

    delta: Dict[str, Any] = {"mean_total_score": None, "mean_contributions": {}}
    if wins and losses:
        delta["mean_total_score"] = float(w["mean_total_score"]) - float(l_["mean_total_score"])  # type: ignore[arg-type]
        wmc = w["mean_contributions"]  # type: ignore[assignment]
        lmc = l_["mean_contributions"]  # type: ignore[assignment]
        delta["mean_contributions"] = {k: float(wmc[k]) - float(lmc[k]) for k in CONTRIB_KEYS}

    return {
        "confidence_score_trades_with_attribution": len(scored),
        "winners": w,
        "losers": l_,
        "flat_net_pnl_zero": f,
        "winner_minus_loser": delta,
        "interpretation": (
            "Positive winner_minus_loser.mean_contributions[k] suggests winners had more of that "
            "component on average — consider increasing conf_weight_* for that pillar. "
            "Compare share_with_flag between winners and losers for boolean gates."
        ),
    }
