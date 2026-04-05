"""
REPORT-01 / D-09–D-11: Plotly candlestick + SVP panel + trade overlays.
Phase 7: equity curve (D-05/D-06), dual NQ+ES charts (D-07–D-09).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.lvn import LVNZone
from src.position import TradeResult
from src.volume_profile import VolumeProfile


@dataclass
class TradeChartContext:
    """Optional confluence overlays for dual-panel trade charts (Phase 7)."""

    bias: Optional[str] = None
    upper_ratio: Optional[float] = None
    sp_zones: Optional[Sequence[Any]] = None
    structural_note: Optional[str] = None


def _window_slice(bars_df: pd.DataFrame, entry_i: int, exit_i: int) -> pd.DataFrame:
    lo = max(0, entry_i - 60)
    hi = min(len(bars_df) - 1, exit_i + 30)
    return bars_df.iloc[lo : hi + 1]


def _candle_x(win: pd.DataFrame) -> List[Any]:
    idx = win.index
    if isinstance(idx, pd.DatetimeIndex):
        return list(idx)
    return list(range(len(win)))


def build_trade_chart(
    trade: TradeResult,
    bars_df: pd.DataFrame,
    volume_profile: VolumeProfile,
    lvn_zone: LVNZone,
    fill_timestamps: Optional[Sequence[Union[pd.Timestamp, Any]]] = None,
    instrument_symbol: str = "NQ",
) -> go.Figure:
    """
    Candlestick (left) + horizontal volume-at-price (right), shared price scale.
    Overlays: entry/SL/TP1/TP2 hlines, LVN band (yellow), optional vertical markers at fills.
    """
    win = _window_slice(bars_df, trade.entry_bar_index, trade.exit_bar_index)
    x = _candle_x(win)

    fig = make_subplots(
        rows=1,
        cols=2,
        shared_yaxes=True,
        column_widths=[0.72, 0.28],
        horizontal_spacing=0.02,
    )

    fig.add_trace(
        go.Candlestick(
            x=x,
            open=win["open_nq"],
            high=win["high_nq"],
            low=win["low_nq"],
            close=win["close_nq"],
            name="NQ",
            increasing_line_color="#26a69a",
            decreasing_line_color="#ef5350",
        ),
        row=1,
        col=1,
    )

    prices: List[float] = []
    vols: List[float] = []
    for i in range(len(volume_profile.volumes)):
        v = float(volume_profile.volumes[i])
        if v <= 0:
            continue
        prices.append(volume_profile.get_price_at(i))
        vols.append(v)
    fig.add_trace(
        go.Bar(x=vols, y=prices, orientation="h", name="SVP", marker_color="rgba(100,120,180,0.55)"),
        row=1,
        col=2,
    )

    stype = str(trade.setup_type).replace(" ", "_")
    title = (
        f"{instrument_symbol} | {trade.session_date} | {trade.direction} | {stype} | "
        f"PnL: ${trade.net_pnl:.2f}"
    )
    fig.update_layout(
        title_text=title,
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        showlegend=True,
        margin=dict(l=48, r=24, t=56, b=40),
    )

    y0 = float(lvn_zone.low)
    y1 = float(lvn_zone.high)
    x0 = x[0] if x else 0
    x1 = x[-1] if x else 1
    fig.add_shape(
        type="rect",
        x0=x0,
        x1=x1,
        y0=y0,
        y1=y1,
        fillcolor="yellow",
        opacity=0.12,
        layer="below",
        line_width=0,
        row=1,
        col=1,
    )

    fig.add_hline(y=trade.entry_price, line_color="blue", line_width=1, row=1, col=1)
    fig.add_hline(y=trade.stop_price, line_color="red", line_width=1, row=1, col=1)
    fig.add_hline(
        y=trade.target_price,
        line_color="green",
        line_dash="dash",
        line_width=1,
        row=1,
        col=1,
    )
    fig.add_hline(y=trade.tp2_price, line_color="green", line_width=1, row=1, col=1)

    if fill_timestamps:
        for t in fill_timestamps:
            fig.add_vline(x=t, line_dash="dash", line_color="rgba(255,255,255,0.35)", row=1, col=1)

    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_xaxes(title_text="Time", row=1, col=1)
    fig.update_xaxes(title_text="Volume", row=1, col=2)

    return fig


def build_equity_curve_figure(
    dates: Sequence[str],
    equity: pd.Series,
    *,
    start_equity: float = 100_000.0,
    top_episodes: Optional[List[Dict[str, Any]]] = None,
) -> go.Figure:
    """Phase 7 D-05: equity line, drawdown fill vs running peak, start-capital hline, DD annotations."""
    xd = pd.to_datetime(list(dates))
    eq = equity.astype(float).values
    peak = np.maximum.accumulate(eq)
    fig = go.Figure()
    fig.add_hline(y=start_equity, line_dash="dot", line_color="gray", annotation_text=f"${start_equity:,.0f}")
    fig.add_trace(
        go.Scatter(
            x=xd,
            y=peak,
            mode="lines",
            line=dict(width=0),
            showlegend=False,
            hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=xd,
            y=eq,
            mode="lines",
            line=dict(color="#26a69a", width=2),
            fill="tonexty",
            fillcolor="rgba(239,83,80,0.18)",
            name="Equity",
        )
    )
    anns: List[Any] = []
    if top_episodes:
        for ep in top_episodes[:3]:
            label = f"{ep.get('peak_date','?')} → {ep.get('trough_date','?')}"
            anns.append(
                dict(
                    x=pd.to_datetime(ep.get("trough_date", dates[0])),
                    y=float(eq.min()),
                    text=label,
                    showarrow=True,
                    arrowhead=2,
                    ax=0,
                    ay=-40,
                )
            )
    fig.update_layout(
        title="Compounded equity & drawdown",
        template="plotly_dark",
        annotations=anns,
        margin=dict(l=48, r=24, t=56, b=40),
    )
    fig.update_xaxes(title_text="Date")
    fig.update_yaxes(title_text="Equity ($)")
    return fig


def write_equity_curve_html(run_root: Path, run_timestamp: str, fig: go.Figure) -> Path:
    """Phase 7 D-06: equity_curve_{run_timestamp}.html under run root."""
    run_root.mkdir(parents=True, exist_ok=True)
    out = run_root / f"equity_curve_{run_timestamp}.html"
    fig.write_html(str(out), include_plotlyjs="cdn", full_html=True)
    return out


def build_trade_chart_dual(
    trade: TradeResult,
    bars_df: pd.DataFrame,
    volume_profile: VolumeProfile,
    lvn_zone: LVNZone,
    fill_timestamps: Optional[Sequence[Union[pd.Timestamp, Any]]] = None,
    instrument_symbol: str = "NQ",
    chart_ctx: Optional[TradeChartContext] = None,
) -> go.Figure:
    """
    Phase 7 D-07–D-09: NQ (row1) + ES (row2) candles, shared x; SVP on NQ row col2.
    """
    win = _window_slice(bars_df, trade.entry_bar_index, trade.exit_bar_index)
    x = _candle_x(win)

    fig = make_subplots(
        rows=2,
        cols=2,
        shared_xaxes=True,
        row_heights=[0.72, 0.28],
        column_widths=[0.72, 0.28],
        vertical_spacing=0.06,
        horizontal_spacing=0.02,
    )

    fig.add_trace(
        go.Candlestick(
            x=x,
            open=win["open_nq"],
            high=win["high_nq"],
            low=win["low_nq"],
            close=win["close_nq"],
            name="NQ",
            increasing_line_color="#26a69a",
            decreasing_line_color="#ef5350",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Candlestick(
            x=x,
            open=win["open_es"],
            high=win["high_es"],
            low=win["low_es"],
            close=win["close_es"],
            name="ES",
            increasing_line_color="#66bb6a",
            decreasing_line_color="#ef9a9a",
        ),
        row=2,
        col=1,
    )

    prices: List[float] = []
    vols: List[float] = []
    for i in range(len(volume_profile.volumes)):
        v = float(volume_profile.volumes[i])
        if v <= 0:
            continue
        prices.append(volume_profile.get_price_at(i))
        vols.append(v)
    fig.add_trace(
        go.Bar(x=vols, y=prices, orientation="h", name="SVP", marker_color="rgba(100,120,180,0.55)"),
        row=1,
        col=2,
    )

    stype = str(trade.setup_type).replace(" ", "_")
    title = (
        f"{instrument_symbol}+ES | {trade.session_date} | {trade.direction} | {stype} | "
        f"PnL: ${trade.net_pnl:.2f}"
    )
    if chart_ctx and chart_ctx.bias:
        title = f"BIAS: {chart_ctx.bias} | " + title
    fig.update_layout(
        title_text=title,
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        showlegend=True,
        margin=dict(l=48, r=24, t=72, b=40),
    )

    y0 = float(lvn_zone.low)
    y1 = float(lvn_zone.high)
    x0 = x[0] if x else 0
    x1 = x[-1] if x else 1
    fig.add_shape(
        type="rect",
        x0=x0,
        x1=x1,
        y0=y0,
        y1=y1,
        fillcolor="yellow",
        opacity=0.12,
        layer="below",
        line_width=0,
        row=1,
        col=1,
    )
    if chart_ctx and chart_ctx.sp_zones:
        for sp in chart_ctx.sp_zones:
            if not (hasattr(sp, "low") and hasattr(sp, "high")):
                continue
            lo, hi = float(sp.low), float(sp.high)
            fig.add_shape(
                type="rect",
                x0=x0,
                x1=x1,
                y0=lo,
                y1=hi,
                fillcolor="green",
                opacity=0.1,
                layer="below",
                line_width=0,
                row=1,
                col=1,
            )

    fig.add_hline(y=trade.entry_price, line_color="blue", line_width=1, row=1, col=1)
    fig.add_hline(y=trade.stop_price, line_color="red", line_width=1, row=1, col=1)
    fig.add_hline(
        y=trade.target_price,
        line_color="green",
        line_dash="dash",
        line_width=1,
        row=1,
        col=1,
    )
    fig.add_hline(y=trade.tp2_price, line_color="green", line_width=1, row=1, col=1)

    if fill_timestamps:
        for t in fill_timestamps:
            fig.add_vline(x=t, line_dash="dash", line_color="rgba(255,255,255,0.35)", row=1, col=1)

    if chart_ctx and chart_ctx.structural_note:
        fig.add_annotation(
            text=chart_ctx.structural_note,
            xref="paper",
            yref="paper",
            x=0.01,
            y=0.99,
            showarrow=False,
            xanchor="left",
            yanchor="top",
            font=dict(size=10),
        )

    fig.update_yaxes(title_text="NQ", row=1, col=1)
    fig.update_yaxes(title_text="ES", row=2, col=1)
    fig.update_xaxes(title_text="Time", row=2, col=1)
    fig.update_xaxes(title_text="Volume", row=1, col=2)
    return fig
