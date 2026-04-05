"""
End-to-end backtest: session loop, signal generation, entry evaluation, RunWriter + metrics.
"""

from __future__ import annotations

from datetime import time
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd
from tqdm import tqdm
from zoneinfo import ZoneInfo

from src.backtest import run_session_backtest
from src.backtest_diagnostics import BacktestDiagnostics
from src.config import AppConfig, RunPaths, effective_thresholds_for_relax, run_paths_from_config
from src.core import get_session_indicators
from src.data_loader import DataLoader
from src.entry import (
    AggressiveLvnState,
    evaluate_aggressive_long,
    evaluate_aggressive_short,
    evaluate_three_step_long,
    evaluate_three_step_short,
    explain_pre_entry_failure,
    first_blocker_aggressive_long,
    first_blocker_aggressive_short,
    first_blocker_three_step_long,
    first_blocker_three_step_short,
    notify_aggressive_trade_completed,
    register_aggressive_pending,
)
from src.entry_confidence import evaluate_confidence_long, evaluate_confidence_short
from src.lvn import ConfluenceRegistry, LVNDetector
from src.metrics import compute_and_write_institutional_summaries
from src.position import SessionTradeBudget, TradeResult, TradeSetup
from src.reporting import RunWriter
from src.session import SessionManager
from src.single_prints import detect_single_prints, update_sp_overnight_respect
from src.smt import detect_smt_at_bar
from src.ismt import detect_ismt_at_bar, invalidate_ismt_if_trade_through
from src.swings import SwingDetector, SwingRegistry
from src.tpo import compute_tpo_bias
from src.volume_profile import build_volume_profile

NY = ZoneInfo("America/New_York")


def _session_day_str(sid: pd.Timestamp) -> str:
    if hasattr(sid, "strftime"):
        return sid.strftime("%Y-%m-%d")
    return str(sid)[:10]


def _filter_sessions(
    sessions: List[pd.Timestamp], start_date: str, end_date: str
) -> List[pd.Timestamp]:
    lo = pd.Timestamp(start_date, tz=NY)
    hi = pd.Timestamp(end_date, tz=NY)
    return [s for s in sessions if lo <= s <= hi]


def _trade_outcome_counts(trades: List[TradeResult]) -> Tuple[int, int, int]:
    wins = sum(1 for t in trades if t.net_pnl > 0)
    losses = sum(1 for t in trades if t.net_pnl < 0)
    flat = len(trades) - wins - losses
    return wins, losses, flat


def _console_trade_summary(trades: List[TradeResult]) -> str:
    n = len(trades)
    if n == 0:
        return "trades=0"
    w, l_, f = _trade_outcome_counts(trades)
    pnl = sum(float(t.net_pnl) for t in trades)
    return f"trades={n} win={w} loss={l_} flat={f} net_pnl=${pnl:,.2f}"


def run_full_backtest(
    cfg: AppConfig,
    *,
    start_date: str,
    end_date: str,
    nq_path: str = "nq_1min_10y.parquet",
    es_path: str = "1Min_ES.parquet",
    write_institutional_summaries: bool = True,
    config_path: str = "config.yaml",
    show_progress: bool = True,
    diagnostics: bool = False,
) -> Tuple[RunPaths, List[TradeResult]]:
    nq_p = Path(nq_path)
    es_p = Path(es_path)
    if not nq_p.is_file() or not es_p.is_file():
        raise FileNotFoundError(
            f"Parquet data not found. Expected {nq_p.resolve()} and {es_p.resolve()}."
        )

    paths = run_paths_from_config(cfg)
    writer = RunWriter(paths, instrument_symbol=cfg.nq.symbol)
    all_trades: List[TradeResult] = []
    global_trade_idx = 0

    loader = DataLoader(nq_path, es_path, start_date=start_date, end_date=end_date)
    stream = loader.get_synchronized_stream()
    manager = SessionManager(stream)
    sessions = _filter_sessions(manager.sessions, start_date, end_date)

    lvn_confluence = ConfluenceRegistry(num_sessions=2)
    prior_session_sp_zones: list = []
    diag = BacktestDiagnostics() if diagnostics else None
    sessions_without_trade = 0

    n_sess = len(sessions)
    print(
        f"Full backtest {start_date} .. {end_date} | "
        f"{n_sess} sessions | output: {paths.run_root}"
    )

    pbar = (
        tqdm(
            total=n_sess,
            desc="Sessions",
            unit="session",
            dynamic_ncols=True,
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}{postfix}]",
        )
        if show_progress and n_sess > 0
        else None
    )

    def _refresh_progress_postfix() -> None:
        if pbar is None:
            return
        pbar.set_postfix_str(_console_trade_summary(all_trades), refresh=True)

    for si, sid in enumerate(sessions):
        trades_at_session_start = len(all_trades)
        session_df = manager.get_session(sid)
        if session_df.empty:
            if len(all_trades) == trades_at_session_start:
                sessions_without_trade += 1
            if pbar is not None:
                pbar.update(1)
            elif not show_progress and n_sess > 0 and (si + 1) % 10 == 0:
                print(
                    f"  progress sessions {si + 1}/{n_sess} | "
                    f"{_console_trade_summary(all_trades)}"
                )
            continue
        day_str = _session_day_str(sid)

        if diag is not None:
            diag.sessions_total += 1

        n_relax = cfg.thresholds.backtest_relax_after_sessions_without_trade
        relax = n_relax > 0 and sessions_without_trade >= n_relax
        eff_th = effective_thresholds_for_relax(cfg.thresholds, relax)

        pre_rth = manager.get_pre_market_bars(session_df)
        bias, _ = compute_tpo_bias(pre_rth, cfg.nq.tick_size)
        bias_s = bias.value

        vp_pre = build_volume_profile(day_str, pre_rth, cfg.nq.tick_size)
        lvn_detector = LVNDetector(cfg.thresholds)
        lvn_candidates = lvn_detector.detect_lvn_candidates(vp_pre)
        valid_lvns = [
            l
            for l in lvn_candidates
            if lvn_confluence.check_confluence(
                l.midpoint,
                cfg.nq.tick_size,
                eff_th.confluence_alignment_ticks,
                eff_th.confluence_pass_if_no_prior_history,
            )
        ]

        if diag is not None:
            if bias_s == "NEUTRAL":
                diag.sessions_neutral_bias += 1
            if not lvn_candidates:
                diag.sessions_zero_lvn_candidates += 1
            if not valid_lvns:
                diag.sessions_zero_valid_lvns += 1

        for sp_zone in prior_session_sp_zones:
            update_sp_overnight_respect([sp_zone], pre_rth, cfg.nq.tick_size)
        respected_sps = [z for z in prior_session_sp_zones if z.respected_overnight]

        bars = get_session_indicators(session_df, eff_th)
        if "session_id" in bars.columns:
            bars = bars.drop(columns=["session_id"])

        rth = manager.get_rth_bars(session_df)
        rth_ts_set = set(rth.index)

        nq_det = SwingDetector(
            lookback=cfg.thresholds.confirmed_swing_lookback,
            min_swing_ticks=cfg.thresholds.min_swing_ticks,
            tick_size=cfg.nq.tick_size,
        )
        es_det = SwingDetector(
            lookback=cfg.thresholds.confirmed_swing_lookback,
            min_swing_ticks=cfg.thresholds.min_swing_ticks,
            tick_size=cfg.es.tick_size,
        )
        nq_reg = SwingRegistry(buffer_size=5)
        es_reg = SwingRegistry(buffer_size=5)
        ismt_signals: list = []
        smt_signals: list = []
        closes = bars["close_nq"].astype(float).values

        session_budget = SessionTradeBudget(
            max_trades=cfg.thresholds.max_trades_per_session,
            opens_this_session=0,
        )
        aggressive_state = AggressiveLvnState()
        setups_accepted = 0

        if pbar is not None:
            pbar.set_description(f"Sessions [{day_str}]")

        for i in range(len(bars)):
            bar = bars.iloc[i]
            ts = bar.name
            for s in nq_det.process_bar(ts, float(bar["high_nq"]), float(bar["low_nq"])):
                nq_reg.add_swing(s)
            for s in es_det.process_bar(ts, float(bar["high_es"]), float(bar["low_es"])):
                es_reg.add_swing(s)

            for sig in ismt_signals:
                invalidate_ismt_if_trade_through(sig, closes, sig.confirmed_at)

            atr20 = float(bar["atr_slow"])
            atr5 = float(bar["atr_fast"])
            ni = detect_ismt_at_bar(i, float(bar["close_nq"]), atr20, nq_reg.get_swings())
            if ni is not None:
                ismt_signals.append(ni)
            ns = detect_smt_at_bar(
                bars,
                i,
                nq_reg.get_swings(),
                es_reg.get_swings(),
                atr20,
                cfg.thresholds.smt_min_correlation,
            )
            if ns is not None:
                smt_signals.append(ns)

            if ts in rth_ts_set:
                for lvn in valid_lvns:
                    lvn_detector.update_lvn_consolidation(lvn, bar)

            if ts not in rth_ts_set:
                continue

            if diag is not None:
                diag.rth_bars_total += 1

            # Legacy: skip NEUTRAL. Confidence model may still enter (partial confluence).
            if not eff_th.use_entry_confidence_model and bias_s == "NEUTRAL":
                continue

            if not session_budget.can_enter():
                continue

            prior = [bars.iloc[j] for j in range(max(0, i - 10), i)]
            bt = ts.time() if hasattr(ts, "time") else time(12, 0)

            if diag is not None and valid_lvns:
                diag.rth_bars_with_valid_lvns += 1
                if not eff_th.use_entry_confidence_model:
                    for lvn in valid_lvns:
                        if bias_s == "BULLISH":
                            b = first_blocker_three_step_long(
                                i,
                                bar,
                                prior,
                                lvn,
                                respected_sps,
                                ismt_signals,
                                smt_signals,
                                cfg.nq.tick_size,
                                eff_th,
                            )
                            if b:
                                diag.record_blocker(b)
                            b = first_blocker_aggressive_long(
                                i,
                                bar,
                                lvn,
                                bias_s,
                                aggressive_state,
                                cfg.nq.tick_size,
                                eff_th,
                            )
                            if b:
                                diag.record_blocker(b)
                        elif bias_s == "BEARISH":
                            b = first_blocker_three_step_short(
                                i,
                                bar,
                                prior,
                                lvn,
                                respected_sps,
                                ismt_signals,
                                smt_signals,
                                cfg.nq.tick_size,
                                eff_th,
                            )
                            if b:
                                diag.record_blocker(b)
                            b = first_blocker_aggressive_short(
                                i,
                                bar,
                                lvn,
                                bias_s,
                                aggressive_state,
                                cfg.nq.tick_size,
                                eff_th,
                            )
                            if b:
                                diag.record_blocker(b)

            def try_setup(setup: Optional[TradeSetup]) -> None:
                nonlocal global_trade_idx, setups_accepted, all_trades
                if setup is None:
                    return
                pef = explain_pre_entry_failure(
                    entry_price=float(setup.entry_price),
                    stop_price=float(setup.stop_price),
                    target_price=float(setup.target_price),
                    bias=bias_s,
                    atr20=atr20,
                    tick_size=cfg.nq.tick_size,
                    bar_time=bt,
                    session_setup_count=setups_accepted,
                    allow_neutral_bias=eff_th.use_entry_confidence_model,
                )
                if pef is not None:
                    if diag is not None:
                        diag.record_pre_entry(pef)
                    return
                if diag is not None:
                    diag.setups_built += 1
                if setup.setup_type == "AGGRESSIVE_LEDGE":
                    register_aggressive_pending(setup, aggressive_state)
                setups_accepted += 1
                vol_profile = build_volume_profile(day_str, session_df, cfg.nq.tick_size)
                results = run_session_backtest(
                    bars_df=bars,
                    setups=[setup],
                    instrument=cfg.nq,
                    thresholds=eff_th,
                    paths=paths,
                    session_date=day_str,
                    volume_profile=vol_profile,
                    writer=writer,
                    session_budget=session_budget,
                    trade_index_offset=global_trade_idx,
                    write_institutional_summaries=False,
                    config_path=config_path,
                )
                for tr in results:
                    all_trades.append(tr)
                    global_trade_idx += 1
                    if tr.setup_type == "AGGRESSIVE_LEDGE":
                        notify_aggressive_trade_completed(tr.lvn_id, aggressive_state)
                    if diag is not None:
                        diag.trades_recorded += 1
                    _refresh_progress_postfix()
                    if not show_progress:
                        print(f"  [{day_str}] {_console_trade_summary(all_trades)}")

            for lvn in valid_lvns:
                if not session_budget.can_enter():
                    break
                
                # Hierarchy: THREE_STEP > AGGRESSIVE_LEDGE > CONFIDENCE_SCORE
                best_setup: Optional[TradeSetup] = None
                
                # 1. Check Three-Step (Strict)
                s3l = evaluate_three_step_long(i, bar, prior, lvn, respected_sps, ismt_signals, smt_signals, atr5, atr20, cfg.nq.tick_size, eff_th)
                s3s = evaluate_three_step_short(i, bar, prior, lvn, respected_sps, ismt_signals, smt_signals, atr5, atr20, cfg.nq.tick_size, eff_th)
                best_setup = s3l or s3s
                
                # 2. Check Aggressive Ledge if no Three-Step
                if best_setup is None:
                    sal = evaluate_aggressive_long(i, bar, lvn, bias_s, atr5, atr20, respected_sps, aggressive_state, cfg.nq.tick_size, thresholds=eff_th)
                    sas = evaluate_aggressive_short(i, bar, lvn, bias_s, atr5, atr20, respected_sps, aggressive_state, cfg.nq.tick_size, thresholds=eff_th)
                    best_setup = sal or sas
                    
                # 3. Check Confidence Score if still no setup and model enabled
                if best_setup is None and eff_th.use_entry_confidence_model:
                    # In backtest loop, we skip this if strict setups already hit for same bar/lvn
                    scl = evaluate_confidence_long(i, bar, prior, lvn, bias_s, respected_sps, ismt_signals, smt_signals, atr5, atr20, cfg.nq.tick_size, eff_th)
                    scs = evaluate_confidence_short(i, bar, prior, lvn, bias_s, respected_sps, ismt_signals, smt_signals, atr5, atr20, cfg.nq.tick_size, eff_th)
                    best_setup = scl or scs
                
                if best_setup:
                    try_setup(best_setup)

        if len(all_trades) == trades_at_session_start:
            sessions_without_trade += 1
        else:
            sessions_without_trade = 0

        if diag is not None:
            n_respected = sum(1 for z in prior_session_sp_zones if z.respected_overnight)
            diag.maybe_snapshot_session(
                session_date=day_str,
                bias=bias_s,
                n_lvn_candidates=len(lvn_candidates),
                n_valid_lvns=len(valid_lvns),
                n_sp_zones=len(prior_session_sp_zones),
                n_respected_sp=n_respected,
                n_ismt=len(ismt_signals),
                n_smt=len(smt_signals),
                confluence_history_sessions=len(lvn_confluence.history),
            )

        current_mids = [l.midpoint for l in lvn_candidates]
        lvn_confluence.add_session_midpoints(current_mids)
        full_vp = build_volume_profile(day_str, session_df, cfg.nq.tick_size)
        prior_session_sp_zones = detect_single_prints(session_df, full_vp, cfg.nq.tick_size)

        if pbar is not None:
            pbar.update(1)
            _refresh_progress_postfix()
        elif not show_progress and n_sess > 0:
            if (si + 1) % 10 == 0 or si + 1 == n_sess:
                print(
                    f"  progress sessions {si + 1}/{n_sess} | "
                    f"{_console_trade_summary(all_trades)}"
                )

    if pbar is not None:
        pbar.close()

    writer.finalize_summary()
    cfg_p = Path(config_path)
    yaml_text = cfg_p.read_text(encoding="utf-8") if cfg_p.is_file() else ""

    if write_institutional_summaries:
        compute_and_write_institutional_summaries(
            trades=all_trades,
            paths=paths,
            account_size=cfg.thresholds.account_size,
            config_yaml_text=yaml_text,
            instrument_symbol=cfg.nq.symbol,
            run_timestamp=paths.run_timestamp,
            config_path=config_path,
        )

    if diag is not None:
        out_diag = paths.run_root / "trade_diagnostics.json"
        diag.write_json(out_diag)
        diag.print_summary()
        print(f"Diagnostics written to {out_diag}")

    print(
        f"Done. {_console_trade_summary(all_trades)} | "
        f"sessions={n_sess} | run folder: {paths.run_root}"
    )
    return paths, all_trades
