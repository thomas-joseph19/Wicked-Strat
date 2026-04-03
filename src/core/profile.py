import polars as pl
import numpy as np

class VolumeProfileEngine:
    """
    Handles interpolation, session profile building, and stat anomaly detection
    for Session Volume Profiles (SVP).
    """

    def __init__(self, tick_size_int: int = 25):
        # NQ/ES is 0.25 (Int 25)
        self.tick_size_int = tick_size_int 

    def interpolate_volume(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Req 2.1: Distribute 1-min volume linearly across all price levels 
        within a bar to create synthetic tick distributions.
        """
        return (
            df.with_columns(
                ((pl.col("high_int") - pl.col("low_int")) // self.tick_size_int + 1).alias("tick_count")
            )
            .with_columns(
                (pl.col("volume") / pl.col("tick_count")).alias("vol_per_tick")
            )
            .with_columns(
                pl.struct(["low_int", "high_int"]).map_elements(
                    lambda x: list(range(x["low_int"], x["high_int"] + self.tick_size_int, self.tick_size_int)),
                    return_dtype=pl.List(pl.Int32)
                ).alias("price_tick")
            )
            .explode("price_tick")
            .select(["session_date", "timestamp", "price_tick", "vol_per_tick"])
        )

    def build_session_profiles(self, tick_df: pl.DataFrame) -> pl.DataFrame:
        """
        Groups tick-level volume into total session profiles per price.
        """
        return (
            tick_df.group_by(["session_date", "price_tick"]).agg(
                pl.col("vol_per_tick").sum().alias("volume")
            ).sort(["session_date", "price_tick"])
        )

    def compute_svp_metrics(self, session_date, profile_df: pl.DataFrame) -> dict:
        """
        Req 2.2: POC, V_total, Mean, Std Dev, and 70% Value Area.
        """
        df = profile_df.filter(pl.col("session_date") == session_date).sort("price_tick")
        if df.is_empty():
            return None
            
        prices = df.get_column("price_tick").to_numpy()
        volumes = df.get_column("volume").to_numpy()
        
        v_total = volumes.sum()
        max_idx = np.argmax(volumes)
        poc = prices[max_idx]
        
        v_mean = volumes.mean()
        v_std = volumes.std()
        
        # Value Area (70% expansion from POC)
        target_vol = 0.70 * v_total
        
        low_idx = max_idx
        high_idx = max_idx
        current_vol = volumes[max_idx]
        
        while current_vol < target_vol:
            up_vol = volumes[high_idx + 1] if high_idx + 1 < len(volumes) else 0
            down_vol = volumes[low_idx - 1] if low_idx - 1 >= 0 else 0
            
            if up_vol == 0 and down_vol == 0:
                break
                
            if up_vol >= down_vol and high_idx + 1 < len(volumes):
                high_idx += 1
                current_vol += up_vol
            elif low_idx - 1 >= 0:
                low_idx -= 1
                current_vol += down_vol
            else:
                break
                
        metrics = {
            "session_date": session_date,
            "v_total": v_total,
            "v_mean": v_mean,
            "v_std": v_std,
            "poc": poc,
            "vah": prices[high_idx],
            "val": prices[low_idx]
        }
        
        return metrics

    def detect_raw_lvns(self, profile_df: pl.DataFrame, metrics: dict) -> pl.DataFrame:
        """
        Req 2.3: Statistical local minimums with 3-tick smoothing.
        """
        df = profile_df.filter(pl.col("session_date") == metrics["session_date"]).sort("price_tick")
        if df.is_empty():
            return df
            
        std = metrics["v_std"] if metrics["v_std"] is not None else 0
        threshold = metrics["v_mean"] - 0.5 * std
        
        return (
            df.with_columns(
                pl.col("volume").rolling_mean(window_size=3, center=True).alias("v_smooth")
            )
            .with_columns(
                (
                    (pl.col("v_smooth") < pl.col("v_smooth").shift(1)) & 
                    (pl.col("v_smooth") < pl.col("v_smooth").shift(-1)) &
                    (pl.col("v_smooth") < threshold)
                ).alias("is_raw_lvn")
            )
            .with_columns(
                (1 - (pl.col("v_smooth") / metrics["v_mean"])).alias("lvn_strength")
            )
            .filter(pl.col("is_raw_lvn") == True)
        )

if __name__ == "__main__":
    from src.data.ingestion import IngestionPipeline
    import sys
    import os
    
    # Ensure src is in import path
    sys.path.append(os.getcwd())
    
    ip = IngestionPipeline()
    try:
        raw = ip.load_parquet("nq_1min_10y.parquet")
        raw = raw.head(1000)
        raw = ip.apply_integer_cast(raw)
        raw = ip.compute_session_bounds(raw)
        
        engine = VolumeProfileEngine()
        ticks = engine.interpolate_volume(raw)
        profiles = engine.build_session_profiles(ticks)
        
        example_day = profiles["session_date"].unique()[0]
        metrics = engine.compute_svp_metrics(example_day, profiles)
        lvns = engine.detect_raw_lvns(profiles, metrics)
        
        print(f"Metrics for {example_day}:")
        for k, v in metrics.items():
            print(f"  {k}: {v}")
        print(f"LVNs found: {len(lvns)}")
        if not lvns.is_empty():
            print(lvns.select(["price_tick", "volume", "v_smooth", "lvn_strength"]).head(10))
    except Exception as e:
        import traceback
        traceback.print_exc()
