"""
Phase 6: Institutional summary.md (9 sections) + summary.json.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Sequence

import pandas as pd

from src.confidence_win_loss import summarize_confidence_by_outcome
from src.position import ExitType, TradeResult

# (start_iso, end_iso) -> label
KNOWN_MARKET_EVENTS: List[tuple[tuple[str, str], str]] = [
    (("2020-02-19", "2020-03-23"), "COVID-19 crash"),
    (("2022-01-03", "2022-10-13"), "2022 rate-hike cycle"),
]


def _event_note_for_drawdown(trough_date: str) -> str:
    for (start, end), name in KNOWN_MARKET_EVENTS:
        if start <= trough_date <= end:
            return name
    return ""


SCRATCH_EPS = 1e-6


def _confidence_outcome_markdown(co: Any) -> List[str]:
    """Markdown block for confidence attribution: winners vs losers."""
    lines: List[str] = [
        "",
        "## Confidence vs outcome (entry score)",
        "",
    ]
    if not isinstance(co, dict):
        lines.append("_No confidence outcome payload._")
        lines.append("")
        return lines
    n = int(co.get("confidence_score_trades_with_attribution", 0) or 0)
    if n <= 0:
        lines.append(str(co.get("note", "_No CONFIDENCE_SCORE trades with attribution._")))
        lines.append("")
        return lines
    lines.append(f"Trades with stored attribution: **{n}**.")
    lines.append("")
    for side in ("winners", "losers"):
        d = co.get(side, {})
        cnt = d.get("count", 0) if isinstance(d, dict) else 0
        if not isinstance(d, dict) or cnt == 0:
            lines.append(f"### {side.title()}: _none_")
            lines.append("")
            continue
        lines.append(f"### {side.title()} (n={cnt})")
        lines.append("")
        lines.append(f"- Mean total score: **{float(d['mean_total_score']):.4f}**")
        mc = d.get("mean_contributions", {})
        lines.append("- Mean contributions (score points):")
        for k in sorted(mc.keys()):
            lines.append(f"  - `{k}`: {float(mc[k]):.4f}")
        lines.append("- Share of trades with flag true:")
        sf = d.get("share_with_flag", {})
        for k in sorted(sf.keys()):
            lines.append(f"  - `{k}`: {float(sf[k]) * 100:.1f}%")
        if d.get("approach_counts"):
            lines.append(f"- Approach mix: `{d['approach_counts']}`")
        if d.get("session_bias_counts"):
            lines.append(f"- Session bias mix: `{d['session_bias_counts']}`")
        if d.get("direction_counts"):
            lines.append(f"- Direction mix: `{d['direction_counts']}`")
        lines.append("")
    dlt = co.get("winner_minus_loser", {})
    if isinstance(dlt, dict) and dlt.get("mean_total_score") is not None:
        lines.append("### Winner − loser (mean)")
        lines.append("")
        lines.append(f"- Δ mean total score: **{float(dlt['mean_total_score']):+.4f}**")
        lines.append("- Δ mean contributions:")
        for k in sorted((dlt.get("mean_contributions") or {}).keys()):
            v = float(dlt["mean_contributions"][k])
            lines.append(f"  - `{k}`: {v:+.4f}")
        lines.append("")
    interp = co.get("interpretation")
    if interp:
        lines.append(f"_{interp}_")
        lines.append("")
    return lines


def build_summary_dict(
    *,
    trades: Sequence[TradeResult],
    daily_df: pd.DataFrame,
    equity_stats: Dict[str, Any],
    risk_stats: Dict[str, Any],
    trade_stats_extra: Dict[str, Any],
    daily_distribution: Dict[str, Any],
    annual_df: pd.DataFrame,
    drawdown_episodes: List[Dict[str, Any]],
    session_diag: Dict[str, Any],
    run_meta: Dict[str, Any],
    config_yaml_text: str,
    warnings: List[str],
) -> Dict[str, Any]:
    """JSON-serializable tree for summary.json + markdown builder input."""
    setup_wins = {
        "THREE_STEP": [0, 0],
        "AGGRESSIVE_LEDGE": [0, 0],
        "CONFIDENCE_SCORE": [0, 0],
    }
    sig_wins = {"ISMT": [0, 0], "SMT": [0, 0]}
    scratch = 0
    for t in trades:
        st = t.setup_type
        if st in setup_wins:
            setup_wins[st][1] += 1
            if t.net_pnl > 0:
                setup_wins[st][0] += 1
        if t.signal_source == 1:
            key = "ISMT"
        elif t.signal_source == 0:
            key = "SMT"
        else:
            key = None
        if key is not None:
            sig_wins[key][1] += 1
            if t.net_pnl > 0:
                sig_wins[key][0] += 1
        if t.exit_type == ExitType.PARTIAL_TP and abs(t.net_pnl) < SCRATCH_EPS:
            scratch += 1

    confidence_outcome = summarize_confidence_by_outcome(trades)

    return {
        "meta": {**run_meta, "config_yaml_text": config_yaml_text},
        "risk_adjusted": risk_stats,
        "equity": equity_stats,
        "trade_stats": {
            **trade_stats_extra,
            "setup_win_rates": {k: (v[0] / v[1] if v[1] else 0.0) for k, v in setup_wins.items()},
            "setup_counts": {k: v[1] for k, v in setup_wins.items()},
            "signal_win_rates": {k: (v[0] / v[1] if v[1] else 0.0) for k, v in sig_wins.items()},
            "signal_counts": {k: v[1] for k, v in sig_wins.items()},
            "scratch_trades": scratch,
        },
        "daily_distribution": daily_distribution,
        "daily": daily_df.to_dict(orient="records") if len(daily_df) else [],
        "annual": annual_df.to_dict(orient="records") if len(annual_df) else [],
        "drawdown_episodes": drawdown_episodes,
        "session_quality": session_diag or _default_session_diag(),
        "confidence_outcome": confidence_outcome,
        "warnings": warnings,
    }


def _default_session_diag() -> Dict[str, Any]:
    return {
        "total_sessions_analyzed": 0,
        "sessions_valid_bias_pct": 0.0,
        "sessions_skipped_neutral": 0,
        "avg_active_lvns": 0.0,
        "avg_lvns_invalidated": 0.0,
        "avg_sp_zones": 0.0,
        "sp_respected_overnight_pct": 0.0,
        "setups_generated": 0,
        "setups_rejected_rr": 0,
        "setups_rejected_sl": 0,
        "setups_taken": 0,
        "note": "Session diagnostics not wired (stub). Phase 7 harness may populate.",
    }


def build_summary_markdown(payload: Dict[str, Any]) -> str:
    """9 sections per 06-CONTEXT D-11 (headings verified by tests)."""
    meta = payload["meta"]
    ra = payload["risk_adjusted"]
    ts = payload["trade_stats"]
    dd = payload["daily_distribution"]
    annual = payload["annual"]
    eps = payload["drawdown_episodes"]
    sq = payload["session_quality"]
    warns = payload["warnings"]
    yaml_text = meta.get("config_yaml_text", "# (no config)\n")

    total_net = ts.get("total_net_pnl", 0.0)
    sharpe = ra.get("sharpe")
    sharpe_s = f"{sharpe:.3f}" if sharpe is not None else "N/A"
    mdd_pct = ra.get("max_drawdown_frac", 0) * 100
    if ra.get("sortino_downside_empty"):
        sortino_cell = "inf (no downside days)"
    elif ra.get("sortino") is not None:
        sortino_cell = f"{ra.get('sortino'):.3f}"
    else:
        sortino_cell = "N/A"

    lines: List[str] = [
        "# Backtest institutional summary",
        "",
        "## Executive Summary",
        "",
        f"This run ({meta.get('instrument', 'NQ')}) recorded **{meta.get('trade_count', 0)}** completed trades with **total net P&L ${total_net:,.2f}**. ",
        f"Risk-adjusted Sharpe (ann.) is **{sharpe_s}**; maximum drawdown (compounded equity) is approximately **{mdd_pct:.2f}%**. ",
        f"Win rate (strictly positive net P&L) is **{ts.get('win_rate', 0)*100:.1f}%**. ",
        "",
        "## Risk-Adjusted Performance",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total net P&L | ${total_net:,.2f} |",
        f"| Total return (approx) | {ra.get('total_return_frac', 0)*100:.4f}% |",
        f"| CAGR (approx) | {(ra.get('cagr_approx') or 0)*100:.4f}% |",
        f"| Sharpe (ann.) | {sharpe_s} |",
        f"| Sortino (ann.) | {sortino_cell} |",
        f"| Calmar | {ra.get('calmar') if ra.get('calmar') is not None else 'N/A'} |",
        f"| Max DD ($) | {ra.get('max_drawdown_dollars', 0):,.2f} |",
        f"| Max DD (%) | {mdd_pct:.4f} |",
        f"| Recovery factor | {ra.get('recovery_factor', 0):.4f} |",
        f"| Profit factor | {ts.get('profit_factor', 0):.4f} |",
        "",
        "## Trade Statistics",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total trades | {ts.get('total_trades', 0)} |",
        f"| Win rate | {ts.get('win_rate', 0)*100:.2f}% |",
        f"| Avg win | ${ts.get('avg_win', 0):,.2f} |",
        f"| Avg loss | ${ts.get('avg_loss', 0):,.2f} |",
        f"| Scratch (PARTIAL_TP, abs(PnL)<epsilon) | {ts.get('scratch_trades', 0)} |",
        "",
        "| Setup | Count | Win rate |",
        "|-------|-------|----------|",
    ]
    for k in ("THREE_STEP", "AGGRESSIVE_LEDGE", "CONFIDENCE_SCORE"):
        c = ts.get("setup_counts", {}).get(k, 0)
        w = ts.get("setup_win_rates", {}).get(k, 0) * 100
        lines.append(f"| {k} | {c} | {w:.1f}% |")
    lines.extend(
        [
            "",
            "| Signal | Count | Win rate |",
            "|--------|-------|----------|",
        ]
    )
    for k in ("ISMT", "SMT"):
        c = ts.get("signal_counts", {}).get(k, 0)
        w = ts.get("signal_win_rates", {}).get(k, 0) * 100
        lines.append(f"| {k} | {c} | {w:.1f}% |")

    lines.extend(_confidence_outcome_markdown(payload.get("confidence_outcome") or {}))

    lines.extend(
        [
            "",
            "## Daily P&L Distribution",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Trading days | {dd.get('trading_days', 0)} |",
            f"| Days with trades | {dd.get('days_with_trades', 0)} |",
            f"| Std (daily return) | {dd.get('std_daily_return', 0):.6f} |",
            f"| Skewness | {dd.get('skewness', 0):.4f} |",
            f"| Kurtosis | {dd.get('kurtosis', 0):.4f} |",
            f"| Best day ($) | {dd.get('best_day_pnl', 0):,.2f} |",
            f"| Worst day ($) | {dd.get('worst_day_pnl', 0):,.2f} |",
            "",
            "## Annual Breakdown",
            "",
            "| Year | Net P&L | Sharpe |",
            "|------|---------|--------|",
        ]
    )
    for row in annual:
        sy = f"{row.get('sharpe'):.3f}" if row.get("sharpe") is not None else "N/A"
        lines.append(f"| {row.get('year')} | ${row.get('net_pnl', 0):,.2f} | {sy} |")

    lines.extend(
        [
            "",
            "## Drawdown Analysis",
            "",
            "| Peak | Trough | Recovery | Depth % | Depth $ | Days |",
            "|------|--------|----------|---------|---------|------|",
        ]
    )
    for ep in eps:
        rec = ep.get("recovery_date") or "—"
        note = _event_note_for_drawdown(str(ep.get("trough_date", "")))
        row = (
            f"| {ep.get('peak_date')} | {ep.get('trough_date')} | {rec} | "
            f"{ep.get('depth_frac', 0)*100:.2f} | {ep.get('depth_dollars', 0):,.0f} | "
            f"{ep.get('duration_calendar_days', 0)} |"
        )
        lines.append(row)
    if eps:
        lines.append("")
        lines.append(
            "Worst drawdown overlap with known stress windows is noted inline when trough falls in a mapped range."
        )

    lines.extend(
        [
            "",
            "## Session & Setup Quality",
            "",
            "| Field | Value |",
            "|-------|-------|",
        ]
    )
    for k, v in sq.items():
        if k == "note":
            continue
        lines.append(f"| {k} | {v} |")
    lines.append("")
    lines.append(sq.get("note", ""))

    lines.extend(
        [
            "",
            "## Parameter Snapshot",
            "",
            "```yaml",
            yaml_text.rstrip(),
            "```",
            "",
            "## Notes & Warnings",
            "",
        ]
    )
    if warns:
        for w in warns:
            lines.append(f"- {w}")
    else:
        lines.append("- None.")
    lines.append("")
    return "\n".join(lines)


def write_run_summaries(run_root: Path, md_text: str, json_obj: Dict[str, Any]) -> tuple[Path, Path]:
    run_root.mkdir(parents=True, exist_ok=True)
    md_path = run_root / "summary.md"
    js_path = run_root / "summary.json"
    md_path.write_text(md_text, encoding="utf-8")
    # strip non-JSON config blob from copy if huge — keep full dict
    with open(js_path, "w", encoding="utf-8") as f:
        json.dump(json_obj, f, indent=2, default=str)
    return md_path, js_path
