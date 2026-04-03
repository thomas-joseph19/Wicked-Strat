import polars as pl
import numpy as np

class StrategyOrchestrator:
    """
    Combines analysis and structural data to generate trade signals (Req 4.1-4.4).
    """

    def __init__(self, rr_min: float = 1.5, tick_size_int: int = 25):
        self.rr_min = rr_min
        self.tick_size_int = tick_size_int

    def detect_signals(self, df: pl.DataFrame, lvns: pl.DataFrame, sps: pl.DataFrame) -> list[dict]:
        """
        Req 4.3: 3-Step Model (Bias -> ISMT -> LVN/SP).
        Req 4.2: Aggressive Ledge (9:30-10:00 AM window).
        """
        # Logic: 
        # For each bar:
        # 1. Check for ISMT (Step 1)
        # 2. Check for structural confluence (Step 2: LVN/SP within 4 ticks)
        # 3. Check for Daily Bias (Step 3)
        
        signals = []
        
        # We need to efficienty join LVNs/SPs by session_date
        # Or just have them in memory
        
        lvn_map = lvns.to_dicts()
        sp_map = sps.to_dicts()
        
        # Bar-by-bar traversal for signal generation (Prevents hindsight)
        for row in df.to_dicts():
            session_date = row["session_date"]
            price_high = row["high_int"]
            price_low = row["low_int"]
            price_close = row["close_int"]
            
            # Step 1: Trigger (ISMT)
            trigger_bearish = row["is_bearish_ismt"]
            trigger_bullish = row["is_bullish_ismt"]
            
            if not (trigger_bearish or trigger_bullish):
                # Check for Ledge Override (9:30-10:00 AM ET)
                # Timestamp is America/New_York
                hour = row["timestamp"].hour
                minute = row["timestamp"].minute
                is_ledge_window = (hour == 9 and 30 <= minute <= 59)
                
                # Ledge: rejection of major node + bias confirmation
                # For V1, we'll focus strictly on ISMT triggers for now or simplify ledge
                pass
                
            # Step 2: Structural Confluence (Within 4 ticks = 100 units)
            # Find closest valid node in current session
            current_lvns = [l for l in lvn_map if l["session_date"] == session_date and not l.get("is_invalidated", False)]
            current_sps = [s for s in sp_map if s["session_date"] == session_date]
            
            nodes = current_lvns + current_sps
            
            def find_confluence(price):
                for node in nodes:
                    if abs(price - node["price_tick"]) <= 100:
                        return node
                return None
                
            confluence = find_confluence(price_close)
            
            if (trigger_bearish or trigger_bullish) and confluence:
                # Step 3: Bias Alignment
                bias = row.get("daily_bias", "Neutral")
                
                if (trigger_bullish and bias == "Bullish") or (trigger_bearish and bias == "Bearish"):
                    # Calculate targets
                    # SL: Beyond the ISMT bar high/low + 2 ticks
                    # TP1: Opposite structural node (for simplicity, we'll use a fixed RR or first SP zone)
                    
                    if trigger_bullish:
                        entry = price_close
                        stop = price_low - 2 * self.tick_size_int
                        risk = entry - stop
                        target = entry + int(self.rr_min * risk) # 1.5 RR Min
                    else:
                        entry = price_close
                        stop = price_high + 2 * self.tick_size_int
                        risk = stop - entry
                        target = entry - int(self.rr_min * risk)
                        
                    if risk > 0:
                        signals.append({
                            "timestamp": row["timestamp"],
                            "session_date": session_date,
                            "direction": "Long" if trigger_bullish else "Short",
                            "entry": entry / 100.0,
                            "stop": stop / 100.0,
                            "target": target / 100.0,
                            "risk": risk / 100.0,
                            "confluence_price": confluence["price_tick"] / 100.0,
                            "type": "3-Step Model"
                        })
                        
        return signals

if __name__ == "__main__":
    from src.data.ingestion import IngestionPipeline
    from src.core.profile import VolumeProfileEngine
    from src.core.structure import StructureEngine
    from src.core.analysis import TechnicalAnalysis
    from src.core.filtering import LVNFilterEngine
    import sys
    import os
    
    sys.path.append(os.getcwd())
    
    ip = IngestionPipeline()
    raw = ip.load_parquet("nq_1min_10y.parquet")
    raw = raw.head(10000)
    raw = ip.apply_integer_cast(raw)
    raw = ip.compute_session_bounds(raw)
    
    # 1. Profile
    engine = VolumeProfileEngine()
    ticks = engine.interpolate_volume(raw)
    profiles = engine.build_session_profiles(ticks)
    
    day_metrics = {}
    for day in profiles["session_date"].unique():
        day_metrics[day] = engine.compute_svp_metrics(day, profiles)
        
    # 2. Raw LVNs
    raw_lvns = pl.concat([engine.detect_raw_lvns(profiles, day_metrics[d]) for d in day_metrics])
    
    # 3. Filtering (No filtering in smoke test for speed)
    
    # 4. Technical Analysis
    ta = TechnicalAnalysis()
    swings = ta.detect_swings(raw)
    ismt = ta.detect_ismt(swings)
    
    # 5. Structure (Bias & Single Prints)
    struct = StructureEngine()
    tpos = struct.calculate_tpos(raw)
    tpos = struct.determine_daily_bias(tpos)
    
    # Merge bias to ismt df
    ismt = ismt.join(tpos.select(["session_date", "daily_bias"]).unique(), on="session_date", how="left")
    
    # 6. Strategy
    orchestrator = StrategyOrchestrator()
    # Dummy SPs for test
    sps = pl.DataFrame({"session_date": [], "price_tick": []})
    
    signals = orchestrator.detect_signals(ismt, raw_lvns, sps)
    
    print(f"Signals detected: {len(signals)}")
    if signals:
        print("\nLatest Signal Example:")
        print(signals[-1])
