from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Dict, Any, List, Optional
import yaml
from pathlib import Path


@dataclass(frozen=True)
class RunPaths:
    """D-14 output layout under a configurable base (D-15 via config.yaml output_dir)."""

    run_root: Path
    csv_path: Path
    charts_dir: Path
    run_timestamp: str


def make_run_paths(output_base: Path, run_ts: Optional[str] = None) -> RunPaths:
    ts = run_ts or datetime.now().strftime("%Y%m%d_%H%M%S")
    run_root = output_base / f"run_{ts}"
    return RunPaths(
        run_root=run_root,
        csv_path=run_root / f"backtest_results_{ts}.csv",
        charts_dir=run_root / f"charts_{ts}",
        run_timestamp=ts,
    )


@dataclass(frozen=True)
class InstrumentConfig:
    symbol: str
    tick_size: float
    point_value: float
    commission_per_side: float

@dataclass(frozen=True)
class StrategyThresholds:
    # ATR periods
    atr_period_fast: int = 5
    atr_period_slow: int = 20
    
    # VP / LVN
    lvn_volume_threshold: float = 0.5  # V_mean - 0.5 * V_std
    lvn_strength_min: float = 0.30
    lvn_poc_buffer_ticks: int = 3
    lvn_min_separation_ticks: int = 4
    lvn_consolidation_bars: int = 3
    lvn_consolidation_crossings: int = 4
    # Multi-session LVN alignment (ticks); PDF: levels align across sessions — widen if too few trades
    confluence_alignment_ticks: float = 2.0
    # If True, when no prior sessions in registry yet, allow all LVN candidates (bootstrap first day)
    confluence_pass_if_no_prior_history: bool = False
    # Prior bars that must hold above/below LVN before touch (default 3 = strict)
    approach_min_prior_closes: int = 3
    # Three-step: require respected overnight SP for TP pillar (False = use TP fallback in build_trade_setup)
    three_step_require_respected_sp: bool = True
    # Backtest research: after this many consecutive sessions with zero new trades, temporarily relax filters
    backtest_relax_after_sessions_without_trade: int = 0
    # Values applied only while relaxed (see full_backtest.merge relaxed thresholds)
    relax_confluence_alignment_ticks: float = 8.0
    relax_confluence_pass_if_no_prior_history: bool = True
    relax_three_step_require_respected_sp: bool = False
    relax_approach_min_prior_closes: int = 2
    relax_aggressive_ledge_window_end: str = "11:30"
    
    # TPO Bias
    tpo_upper_threshold: float = 0.55
    tpo_lower_threshold: float = 0.45
    
    # Single Prints
    sp_volume_filter: float = 0.15
    sp_min_height_ticks: int = 4
    sp_overnight_buffer_ticks: int = 2
    
    # ISMT / SMT
    smt_min_correlation: float = 0.70
    smt_nq_move_atr_mult: float = 0.3
    smt_es_fail_atr_mult: float = 0.1
    ismt_lookback: int = 10
    ismt_sweep_max_atr_mult: float = 2.0
    confirmed_swing_lookback: int = 5
    min_swing_ticks: int = 4
    
    # Entry / Execution
    entry_signal_lookback: int = 5
    aggressive_ledge_window_start: str = "09:25"
    aggressive_ledge_window_end: str = "10:00"
    aggressive_ledge_size_multiplier: float = 0.5
    stop_loss_atr_mult: float = 0.5
    stop_loss_min_ticks: int = 4
    stop_loss_max_atr_mult: float = 1.5
    take_profit_1_exit_pct: float = 0.60
    max_trades_per_session: int = 3
    eod_force_close_time: str = "15:45"
    account_size: float = 100000.0
    risk_per_trade: float = 0.01

    # Confidence-weighted entry (partial confluence → static score; ML may replace weights later)
    use_entry_confidence_model: bool = True
    entry_confidence_threshold: float = 0.6
    relax_entry_confidence_threshold: float = 0.5
    conf_weight_lvn_valid: float = 0.10
    conf_weight_bias_aligned: float = 0.14
    conf_weight_bias_neutral: float = 0.05
    conf_weight_approach_full: float = 0.24
    conf_weight_approach_touch_only: float = 0.08
    conf_weight_approach_closes_only: float = 0.06
    conf_weight_trigger_close: float = 0.16
    conf_weight_structural: float = 0.16
    conf_weight_respected_sp: float = 0.12
    conf_weight_aggressive_window_bonus: float = 0.05


def effective_thresholds_for_relax(t: StrategyThresholds, relax: bool) -> StrategyThresholds:
    """Backtest-only: swap in relax_* fields when dry streak triggers."""
    if not relax:
        return t
    return replace(
        t,
        confluence_alignment_ticks=t.relax_confluence_alignment_ticks,
        confluence_pass_if_no_prior_history=t.relax_confluence_pass_if_no_prior_history,
        three_step_require_respected_sp=t.relax_three_step_require_respected_sp,
        approach_min_prior_closes=t.relax_approach_min_prior_closes,
        aggressive_ledge_window_end=t.relax_aggressive_ledge_window_end,
        entry_confidence_threshold=t.relax_entry_confidence_threshold,
    )


@dataclass(frozen=True)
class AppConfig:
    nq: InstrumentConfig
    es: InstrumentConfig
    thresholds: StrategyThresholds
    output_dir: Path

def load_config(config_path: str = "config.yaml") -> AppConfig:
    with open(config_path, "r") as f:
        data = yaml.safe_load(f)
    
    nq_cfg = InstrumentConfig(**data["nq"])
    es_cfg = InstrumentConfig(**data["es"])
    thresholds = StrategyThresholds(**data["thresholds"])
    output_dir = Path(data["output_dir"])
    
    return AppConfig(nq=nq_cfg, es=es_cfg, thresholds=thresholds, output_dir=output_dir)


def run_paths_from_config(app: AppConfig, run_ts: Optional[str] = None) -> RunPaths:
    return make_run_paths(app.output_dir, run_ts)
