import argparse
import os
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime

from src.config import load_config
from src.data_loader import DataLoader
from src.session import SessionManager
from src.core import get_session_indicators
from src.tpo import compute_tpo_bias
from src.swings import SwingDetector, SwingRegistry
from src.volume_profile import build_volume_profile
from src.lvn import LVNDetector, ConfluenceRegistry
from src.single_prints import detect_single_prints, update_sp_overnight_respect
from src.full_backtest import run_full_backtest


def run_backtest_smoke(config_path: str, start_date: str, end_date: str):
    print(f"--- Wicked LVN/Ledge Backtest Smoke Test ---")
    
    # 1. Load Config
    print(f"Loading config from {config_path}...")
    cfg = load_config(config_path)
    
    # 2. Check Data
    # D-11: Data is in project root. If not, inform.
    nq_path = "nq_1min_10y.parquet"
    es_path = "1Min_ES.parquet"
    
    if not os.path.exists(nq_path) or not os.path.exists(es_path):
        print("Error: Parquet files not found in root. Please ensure they exist.")
        return
        
    # 3. Synchronize Data
    print(f"Synchronizing NQ and ES from {start_date} to {end_date}...")
    loader = DataLoader(nq_path, es_path, start_date=start_date, end_date=end_date)
    stream = loader.get_synchronized_stream()
    print(f"Synchronized Stream: {len(stream)} total bars.")
    
    # 4. Global Registries (Phase 3)
    lvn_confluence = ConfluenceRegistry(num_sessions=2)
    prior_session_sp_zones = []
    
    # 5. Session Orchestration
    print("Initializing SessionManager...")
    manager = SessionManager(stream)
    print(f"Total sessions discovered: {len(manager.sessions)}")
    
    # 5. Smoke Test: Process first 5 sessions
    test_sessions = manager.sessions[:5]
    for sid in test_sessions:
        # sid is now a pd.Timestamp (session day)
        session_df = manager.get_session(sid)
        
        # 5a. TPO Bias Implementation (locked at 9:30 AM)
        pre_rth = manager.get_pre_market_bars(session_df)
        bias, ratio = compute_tpo_bias(pre_rth, cfg.nq.tick_size)
        
        # 5b. Volume Profile & LVN candidates (pre-market locked)
        vp = build_volume_profile(sid.strftime('%Y-%m-%d'), pre_rth, cfg.nq.tick_size)
        lvn_detector = LVNDetector(cfg.thresholds)
        lvn_candidates = lvn_detector.detect_lvn_candidates(vp)
        
        # Filter B: Confluence (LVN-02)
        valid_lvns = [
            l
            for l in lvn_candidates
            if lvn_confluence.check_confluence(
                l.midpoint,
                cfg.nq.tick_size,
                cfg.thresholds.confluence_alignment_ticks,
                cfg.thresholds.confluence_pass_if_no_prior_history,
            )
        ]
        
        # 5c. Single Prints (from PRIOR session, checked for overnight respect)
        # SP zones are detected after a session CLOSES and used for the NEXT session
        for sp_zone in prior_session_sp_zones:
            # Update respect flag using CURRENT pre-market bars
            update_sp_overnight_respect([sp_zone], pre_rth, cfg.nq.tick_size)
            
        respected_sps = [z for z in prior_session_sp_zones if z.respected_overnight]
        
        # 5d. Swing Detection
        detector = SwingDetector(lookback=cfg.thresholds.confirmed_swing_lookback, 
                                 min_swing_ticks=cfg.thresholds.min_swing_ticks,
                                 tick_size=cfg.nq.tick_size)
        registry = SwingRegistry(buffer_size=5)
        
        # RTH Loop for real-time invalidation (Filter D)
        rth_bars = manager.get_rth_bars(session_df)
        for idx, row in session_df.iterrows():
            # Swing Detection
            sws = detector.process_bar(idx, row['high_nq'], row['low_nq'])
            for s in sws:
                registry.add_swing(s)
            
            # LVN Consolidation Invalidation (RTH bars only)
            if idx in rth_bars.index:
                for lvn in valid_lvns:
                    lvn_detector.update_lvn_consolidation(lvn, row)
                    
        # 5e. End-of-Session: Harvest LVNs for next session's confluence
        current_lvn_midpoints = [l.midpoint for l in lvn_candidates]
        lvn_confluence.add_session_midpoints(current_lvn_midpoints)
        
        # 5f. Detect SPs for NEXT session targets
        # Build FULL session profile for SP detection logic (SP-01)
        full_vp = build_volume_profile(sid.strftime('%Y-%m-%d'), session_df, cfg.nq.tick_size)
        prior_session_sp_zones = detect_single_prints(session_df, full_vp, cfg.nq.tick_size)
        
        # 5g. Indicators & Logging
        indicators = get_session_indicators(session_df, cfg.thresholds)
        out_rows = len(indicators)
        lvn_count = len([l for l in valid_lvns if l.valid])
        print(f"  Session {sid.strftime('%Y-%m-%d')}: {out_rows} bars. TPO: {bias.value} | LVNs: {lvn_count} | SPs (respected): {len(respected_sps)} | Swings: {len(registry.current_session_swings)}")
        
    print(f"\n--- Smoke Test PASSED ---")
    print(f"Ready for Phase 2 implementation.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Wicked LVN/Ledge Backtest Engine")
    parser.add_argument("--mode", type=str, default="backtest", choices=["backtest", "ml", "debug"])
    parser.add_argument("--start", type=str, default="2014-01-02", help="Backtest start YYYY-MM-DD")
    parser.add_argument("--end", type=str, default="2026-01-30", help="Backtest end YYYY-MM-DD")
    parser.add_argument("--config", type=str, default="config.yaml", help="Path to YAML config")
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Only process first 5 sessions (no trade CSV / charts).",
    )
    parser.add_argument(
        "--no-metrics",
        action="store_true",
        help="Skip institutional summary.json / extended summary.md (still writes CSV + charts + stub summary).",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable tqdm session bar (still prints a line per completed trade).",
    )
    parser.add_argument(
        "--diagnostics",
        action="store_true",
        help="Write trade_diagnostics.json and print blocker summary (why setups fail).",
    )
    parser.add_argument("--nq", type=str, default="nq_1min_10y.parquet", help="Path to NQ parquet")
    parser.add_argument("--es", type=str, default="1Min_ES.parquet", help="Path to ES parquet")

    args = parser.parse_args()

    if args.mode == "backtest":
        if args.smoke:
            run_backtest_smoke(args.config, args.start, args.end)
        else:
            cfg = load_config(args.config)
            run_full_backtest(
                cfg,
                start_date=args.start,
                end_date=args.end,
                nq_path=args.nq,
                es_path=args.es,
                write_institutional_summaries=not args.no_metrics,
                config_path=args.config,
                show_progress=not args.no_progress,
                diagnostics=args.diagnostics,
            )
    else:
        print(f"Mode {args.mode} not yet implemented.")
        sys.exit(1)
        
