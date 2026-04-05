"""
Single-page Plotly dashboard for institutional backtest metrics (runs with summary.md/json).
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Sequence

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.metrics import compounded_equity_from_returns
from src.position import TradeResult


def _fmt_num(x: Any, *, pct: bool = False, money: bool = False) -> str:
    if x is None:
        return "N/A"
    try:
        v = float(x)
    except (TypeError, ValueError):
        return str(x)
    if np.isnan(v):
        return "N/A"
    if pct:
        return f"{v * 100:.4f}%"
    if money:
        return f"${v:,.2f}"
    return f"{v:.6g}"


def build_metrics_dashboard_figure(
    payload: Dict[str, Any],
    trades: Sequence[TradeResult],
    *,
    account_size: float,
) -> go.Figure:
    """One tall figure: KPI table, equity, daily PnL, histograms, annual, exits, setup/signal rates, drawdowns."""
    meta = payload.get("meta", {})
    ra = payload.get("risk_adjusted", {})
    ts = payload.get("trade_stats", {})
    dd = payload.get("daily_distribution", {})
    annual = payload.get("annual", [])
    eps = payload.get("drawdown_episodes", [])
    sq = payload.get("session_quality", {})
    eq_stats = payload.get("equity", {})
    daily_rows: List[Dict[str, Any]] = payload.get("daily") or []

    sortino_cell = "N/A"
    if ra.get("sortino_downside_empty"):
        sortino_cell = "inf (no downside days)"
    elif ra.get("sortino") is not None:
        sortino_cell = _fmt_num(ra.get("sortino"))

    longs = [t for t in trades if t.direction == "LONG"]
    shorts = [t for t in trades if t.direction == "SHORT"]
    lr, sr = len(longs), len(shorts)
    lw = sum(1 for t in longs if t.net_pnl > 0) / lr if lr else 0.0
    sw = sum(1 for t in shorts if t.net_pnl > 0) / sr if sr else 0.0

    gross = sum(float(t.gross_pnl) for t in trades)
    comm = sum(float(t.total_commission) for t in trades)

    table_header = dict(
        values=["Metric", "Value"],
        fill_color="#1e1e2e",
        font=dict(color="#eee", size=12),
        height=28,
    )
    kpi_cells: List[str] = [
        "Instrument",
        str(meta.get("instrument", "")),
        "Run timestamp",
        str(meta.get("run_timestamp", "")),
        "Trades (count)",
        str(meta.get("trade_count", ts.get("total_trades", 0))),
        "Total net P&L",
        _fmt_num(ts.get("total_net_pnl"), money=True),
        "Gross P&L (sum)",
        _fmt_num(gross, money=True),
        "Total commission",
        _fmt_num(comm, money=True),
        "Total return (frac)",
        _fmt_num(ra.get("total_return_frac"), pct=True),
        "CAGR (approx)",
        _fmt_num(ra.get("cagr_approx"), pct=True),
        "Sharpe (ann.)",
        _fmt_num(ra.get("sharpe")) if ra.get("sharpe") is not None else "N/A",
        "Sortino (ann.)",
        sortino_cell,
        "Calmar",
        _fmt_num(ra.get("calmar")) if ra.get("calmar") is not None else "N/A",
        "Max drawdown (%)",
        _fmt_num(ra.get("max_drawdown_frac"), pct=True),
        "Max drawdown ($)",
        _fmt_num(ra.get("max_drawdown_dollars"), money=True),
        "Recovery factor",
        _fmt_num(ra.get("recovery_factor")),
        "Profit factor",
        _fmt_num(ts.get("profit_factor")),
        "Win rate",
        _fmt_num(ts.get("win_rate"), pct=True),
        "LONG win rate",
        f"{lw * 100:.1f}% (n={lr})",
        "SHORT win rate",
        f"{sw * 100:.1f}% (n={sr})",
        "Avg win",
        _fmt_num(ts.get("avg_win"), money=True),
        "Avg loss",
        _fmt_num(ts.get("avg_loss"), money=True),
        "Scratch trades",
        str(ts.get("scratch_trades", 0)),
        "Trading days",
        str(dd.get("trading_days", 0)),
        "Days with trades",
        str(dd.get("days_with_trades", 0)),
        "Std (daily return)",
        _fmt_num(dd.get("std_daily_return")),
        "Skewness (daily)",
        _fmt_num(dd.get("skewness")),
        "Kurtosis (daily)",
        _fmt_num(dd.get("kurtosis")),
        "Best day ($)",
        _fmt_num(dd.get("best_day_pnl"), money=True),
        "Worst day ($)",
        _fmt_num(dd.get("worst_day_pnl"), money=True),
        "Final equity",
        _fmt_num(eq_stats.get("final_equity"), money=True),
    ]
    for k, v in sorted(sq.items()):
        if k == "note":
            continue
        kpi_cells.extend([str(k), str(v)])

    col1 = kpi_cells[0::2]
    col2 = kpi_cells[1::2]
    table_body = dict(
        values=[col1, col2],
        fill_color="#2a2a3c",
        font=dict(color="#ddd", size=11),
        height=22,
    )

    fig = make_subplots(
        rows=7,
        cols=2,
        specs=[
            [{"type": "table", "colspan": 2}, None],
            [{"type": "scatter", "colspan": 2}, None],
            [{"type": "bar", "colspan": 2}, None],
            [{"type": "histogram"}, {"type": "histogram"}],
            [{"type": "bar"}, {"type": "bar"}],
            [{"type": "bar"}, {"type": "bar"}],
            [{"type": "bar", "colspan": 2}, None],
        ],
        subplot_titles=(
            "Institutional KPIs",
            "",
            "Compounded equity",
            "",
            "Daily net P&L ($)",
            "",
            "Daily return distribution",
            "Per-trade net P&L ($)",
            "Annual net P&L ($)",
            "Trades by exit type",
            "Win rate by setup (%)",
            "Win rate by signal (%)",
            "Drawdown episodes (depth %)",
            "",
        ),
        vertical_spacing=0.055,
        row_heights=[0.15, 0.15, 0.12, 0.14, 0.14, 0.14, 0.16],
    )

    fig.add_trace(go.Table(header=table_header, cells=table_body), row=1, col=1)

    if daily_rows:
        dates = [r["date"] for r in daily_rows]
        rets = [float(r["daily_return"]) for r in daily_rows]
        xd = pd.to_datetime(dates)
        eq = compounded_equity_from_returns(rets, account_size)
        fig.add_trace(
            go.Scatter(x=xd, y=eq, mode="lines", name="Equity", line=dict(color="#26a69a", width=2), showlegend=False),
            row=2,
            col=1,
        )
        pnls = [float(r["daily_net_pnl"]) for r in daily_rows]
        colors = ["#26a69a" if p >= 0 else "#ef5350" for p in pnls]
        fig.add_trace(
            go.Bar(x=xd, y=pnls, name="Daily PnL", marker_color=colors, showlegend=False),
            row=3,
            col=1,
        )
        fig.add_trace(
            go.Histogram(x=rets, nbinsx=40, name="Daily return", marker_color="#7e57c2", showlegend=False),
            row=4,
            col=1,
        )
    else:
        fig.add_annotation(
            text="No daily series",
            xref="x2",
            yref="y2",
            x=0.5,
            y=0.5,
            showarrow=False,
            row=2,
            col=1,
        )

    trade_pnls = [float(t.net_pnl) for t in trades]
    if trade_pnls:
        nb = min(40, max(8, len(trade_pnls)))
        fig.add_trace(
            go.Histogram(x=trade_pnls, nbinsx=nb, name="Trade PnL", marker_color="#42a5f5", showlegend=False),
            row=4,
            col=2,
        )
    else:
        fig.add_annotation(
            text="No trades",
            xref="x5",
            yref="y5",
            x=0.5,
            y=0.5,
            showarrow=False,
            row=4,
            col=2,
        )

    if annual:
        years = [int(r["year"]) for r in annual]
        ypnl = [float(r["net_pnl"]) for r in annual]
        acol = ["#26a69a" if p >= 0 else "#ef5350" for p in ypnl]
        fig.add_trace(
            go.Bar(x=years, y=ypnl, name="Year PnL", marker_color=acol, showlegend=False),
            row=5,
            col=1,
        )
    else:
        fig.add_annotation(text="No annual breakdown", row=5, col=1, xref="x7", yref="y7", x=0.5, y=0.5, showarrow=False)

    if trades:
        ex_ct = Counter(str(t.exit_type) for t in trades)
        fig.add_trace(
            go.Bar(
                x=list(ex_ct.keys()),
                y=list(ex_ct.values()),
                name="Exits",
                marker_color="#ffa726",
                showlegend=False,
            ),
            row=5,
            col=2,
        )
    else:
        fig.add_annotation(text="—", row=5, col=2, xref="x8", yref="y8", x=0.5, y=0.5, showarrow=False)

    setup_rates = ts.get("setup_win_rates") or {}
    setup_counts = ts.get("setup_counts") or {}
    if setup_rates:
        sx = list(setup_rates.keys())
        sy = [float(setup_rates[k]) * 100 for k in sx]
        stext = [f"n={setup_counts.get(k, 0)}" for k in sx]
        fig.add_trace(
            go.Bar(x=sx, y=sy, text=stext, textposition="auto", name="Setup", marker_color="#26c6da", showlegend=False),
            row=6,
            col=1,
        )
    else:
        fig.add_annotation(text="No setup stats", row=6, col=1, xref="x9", yref="y9", x=0.5, y=0.5, showarrow=False)

    sig_rates = ts.get("signal_win_rates") or {}
    sig_counts = ts.get("signal_counts") or {}
    if sig_rates:
        gx = list(sig_rates.keys())
        gy = [float(sig_rates[k]) * 100 for k in gx]
        gtext = [f"n={sig_counts.get(k, 0)}" for k in gx]
        fig.add_trace(
            go.Bar(x=gx, y=gy, text=gtext, textposition="auto", name="Signal", marker_color="#ab47bc", showlegend=False),
            row=6,
            col=2,
        )
    else:
        fig.add_annotation(text="No signal stats", row=6, col=2, xref="x10", yref="y10", x=0.5, y=0.5, showarrow=False)

    if eps:
        labels = [f"{e.get('peak_date', '')} → {e.get('trough_date', '')}" for e in eps]
        depths = [float(e.get("depth_frac", 0)) * 100 for e in eps]
        fig.add_trace(
            go.Bar(
                y=labels,
                x=depths,
                orientation="h",
                name="DD %",
                marker_color="#ef5350",
                showlegend=False,
                text=[f"{d:.2f}%" for d in depths],
                textposition="auto",
            ),
            row=7,
            col=1,
        )
    else:
        fig.add_annotation(
            text="No drawdown episodes above threshold",
            row=7,
            col=1,
            xref="x11",
            yref="y11",
            x=0.5,
            y=0.5,
            showarrow=False,
        )

    title = f"Backtest metrics — {meta.get('instrument', 'NQ')} — {meta.get('run_timestamp', '')}"
    fig.update_layout(
        title_text=title,
        template="plotly_dark",
        height=3200,
        showlegend=False,
        margin=dict(l=48, r=32, t=72, b=40),
    )
    fig.update_xaxes(title_text="Date", row=2, col=1)
    fig.update_yaxes(title_text="Equity ($)", row=2, col=1)
    fig.update_xaxes(title_text="Date", row=3, col=1)
    fig.update_yaxes(title_text="Daily $", row=3, col=1)
    fig.update_xaxes(title_text="Daily return", row=4, col=1)
    fig.update_xaxes(title_text="Trade net P&L ($)", row=4, col=2)
    fig.update_xaxes(title_text="Year", row=5, col=1)
    fig.update_yaxes(title_text="Net $", row=5, col=1)
    fig.update_xaxes(title_text="Exit type", row=5, col=2)
    fig.update_yaxes(title_text="Count", row=5, col=2)
    fig.update_yaxes(title_text="Win rate %", row=6, col=1)
    fig.update_yaxes(title_text="Win rate %", row=6, col=2)
    fig.update_xaxes(title_text="Depth % (negative)", row=7, col=1)

    return fig


def write_metrics_dashboard_html(run_root: Path, run_timestamp: str, fig: go.Figure) -> Path:
    """Write metrics_dashboard_{run_timestamp}.html next to summary.md."""
    run_root.mkdir(parents=True, exist_ok=True)
    out = run_root / f"metrics_dashboard_{run_timestamp}.html"
    fig.write_html(str(out), include_plotlyjs="cdn", full_html=True)
    return out
