"""
Minimal session backtest: bar loop + Position + RunWriter (Phase 5 wiring).
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Sequence

import pandas as pd

from src.config import InstrumentConfig, RunPaths, StrategyThresholds
from src.metrics import compute_and_write_institutional_summaries
from src.plotting import TradeChartContext, build_trade_chart, build_trade_chart_dual
from src.position import Position, PositionState, SessionTradeBudget, TradeResult, TradeSetup
from src.reporting import RunWriter
from src.volume_profile import VolumeProfile, build_volume_profile


def run_session_backtest(
    *,
    bars_df: pd.DataFrame,
    setups: Sequence[TradeSetup],
    instrument: InstrumentConfig,
    thresholds: StrategyThresholds,
    paths: RunPaths,
    session_date: str,
    volume_profile: Optional[VolumeProfile] = None,
    writer: Optional[RunWriter] = None,
    session_budget: Optional[SessionTradeBudget] = None,
    trade_index_offset: int = 0,
    write_institutional_summaries: bool = False,
    config_path: str = "config.yaml",
    use_dual_charts: bool = False,
    chart_ctx: TradeChartContext | None = None,
) -> List[TradeResult]:
    """
    For each setup, advance ``Position`` across ``bars_df`` (iloc indices 0..len-1).
    On close, append CSV + HTML chart and collect ``TradeResult``.

    ``volume_profile`` defaults to a profile built from ``bars_df`` when omitted.
    """
    w = writer or RunWriter(paths, instrument_symbol=instrument.symbol)
    vp = volume_profile or build_volume_profile(session_date, bars_df, instrument.tick_size)
    if vp is None:
        raise ValueError("bars_df must be non-empty to build volume profile")

    results: List[TradeResult] = []
    budget = session_budget or SessionTradeBudget(
        max_trades=thresholds.max_trades_per_session,
        opens_this_session=0,
    )

    for ti, setup in enumerate(setups):
        pos = Position(
            setup,
            instrument,
            thresholds,
            budget,
            trade_index=trade_index_offset + ti,
            session_date=session_date,
        )
        for idx in range(len(bars_df)):
            bar = bars_df.iloc[idx]
            pos.update(bar, idx)
            if pos.state == PositionState.CLOSED and pos.to_trade_result() is not None:
                break

        if pos.state in (PositionState.OPEN_FULL, PositionState.OPEN_PARTIAL) and pos.fills:
            li = len(bars_df) - 1
            if li >= 0:
                pos.force_end_of_session_flat(bars_df.iloc[li], li)

        tr = pos.to_trade_result()
        if tr is None:
            continue
        results.append(tr)
        w.append_trade_csv(tr)
        fill_ts = []
        for f in pos.fills:
            if 0 <= f.bar_index < len(bars_df):
                fi = bars_df.index[f.bar_index]
                fill_ts.append(fi)
        if use_dual_charts:
            fig = build_trade_chart_dual(
                tr,
                bars_df,
                vp,
                setup.lvn_ref,
                fill_timestamps=fill_ts or None,
                instrument_symbol=instrument.symbol,
                chart_ctx=chart_ctx,
            )
        else:
            fig = build_trade_chart(
                tr,
                bars_df,
                vp,
                setup.lvn_ref,
                fill_timestamps=fill_ts or None,
                instrument_symbol=instrument.symbol,
            )
        w.write_trade_html(tr, fig)

    if write_institutional_summaries and results:
        cfg_p = Path(config_path)
        config_yaml_text = (
            cfg_p.read_text(encoding="utf-8") if cfg_p.is_file() else "# config.yaml not found\n"
        )
        compute_and_write_institutional_summaries(
            trades=results,
            paths=paths,
            account_size=thresholds.account_size,
            config_yaml_text=config_yaml_text,
            instrument_symbol=instrument.symbol,
            run_timestamp=paths.run_timestamp,
            config_path=str(config_path),
        )

    return results
