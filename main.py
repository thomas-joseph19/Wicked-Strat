import polars as pl
import sys
import os
import time

# Ensure src is in import path
sys.path.append(os.getcwd())

from src.data.ingestion import IngestionPipeline
from src.core.profile import VolumeProfileEngine
from src.core.structure import StructureEngine
from src.core.analysis import TechnicalAnalysis
from src.core.strategy import StrategyOrchestrator
from src.simulator import BacktestSimulator, MetricsEngine

def main():
    print("🚀 Starting Wicked LVN/Ledge (3-Year Slice Simulation)")
    start_time = time.time()
    
    # 1. Ingestion
    print("\n[1/6] Ingesting Data...")
    ip = IngestionPipeline()
    full_data = ip.load_parquet("nq_1min_10y.parquet")
    
    # Last 1M bars for speed (~2.5 years)
    raw = full_data.tail(1000000)
    print(f"      Processing {len(raw):,} bars from {raw['timestamp'][0]} to {raw['timestamp'][-1]}.")
    
    raw = ip.apply_integer_cast(raw)
    raw = ip.compute_session_bounds(raw)
    
    # 2. Volume Profile Engine
    print("\n[2/6] Building Session Profiles...")
    profile_engine = VolumeProfileEngine()
    ticks = profile_engine.interpolate_volume(raw)
    profiles = profile_engine.build_session_profiles(ticks)
    
    print("\n[3/6] Calculating Session Metrics & LVNs...")
    day_metrics = {}
    all_raw_lvns = []
    
    sessions = profiles["session_date"].unique().sort()
    for session in sessions:
        metrics = profile_engine.compute_svp_metrics(session, profiles)
        if metrics:
            day_metrics[session] = metrics
            all_raw_lvns.append(profile_engine.detect_raw_lvns(profiles, metrics))
            
    raw_lvns = pl.concat(all_raw_lvns)
    print(f"      Identified {len(raw_lvns):,} Raw LVN candidates.")
    
    # 3. Technical Analysis
    print("\n[4/6] Running Technical Analysis (Swings & ISMT)...")
    ta = TechnicalAnalysis()
    swings = ta.detect_swings(raw)
    ismt = ta.detect_ismt(swings)
    
    # 4. Structure & Bias
    print("\n[5/6] Calculating TPO Bias and Single Prints...")
    struct = StructureEngine()
    tpos = struct.calculate_tpos(raw)
    tpos = struct.determine_daily_bias(tpos)
    
    # Merge bias to ismt df
    bias_map = tpos.select(["session_date", "daily_bias"]).unique()
    ismt = ismt.join(bias_map, on="session_date", how="left")
    
    # 5. Signal Orchestration
    print("\n[6/6] Generating Strategy Signals...")
    orchestrator = StrategyOrchestrator()
    sps = pl.DataFrame({"session_date": [], "price_tick": []}) # Placeholder for SPs
    
    signals = orchestrator.detect_signals(ismt, raw_lvns, sps)
    print(f"      Total Signals detected: {len(signals)}")
    
    # 6. Simulator
    print("\n[Final] Executing Backtest Simulation...")
    simulator = BacktestSimulator(raw)
    results = simulator.run_simulation(signals)
    
    metrics_engine = MetricsEngine()
    final_stats = metrics_engine.calculate(results)
    
    duration = time.time() - start_time
    print(f"\n✨ Backtest Complete in {duration:.2f}s")
    print("\n--- PERFORMANCE SUMMARY (3-YEAR SLICE) ---")
    for k, v in final_stats.items():
        print(f"{k.replace('_', ' ').title():<25}: {v}")
    print("------------------------------------------\n")

if __name__ == "__main__":
    main()
