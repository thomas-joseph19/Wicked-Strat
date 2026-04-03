import polars as pl
import numpy as np
from datetime import timedelta

class StructureEngine:
    """
    Handles TPO distributions, daily bias detection, and structural zones (Single Prints).
    """

    def __init__(self, tick_size_int: int = 25):
        self.tick_size_int = tick_size_int

    def calculate_tpos(self, df: pl.DataFrame, bracket_min: int = 30) -> pl.DataFrame:
        """
        Req 2.5: Map price visits in 30-min brackets.
        """
        if df.is_empty():
            return df
            
        # 1. Bracket indexing
        # Aligned to simple truncation for now
        df = df.with_columns(
            pl.col("timestamp").dt.truncate(f"{bracket_min}m").alias("bracket")
        )
        
        # 2. Get high/low per bracket
        brackets = df.group_by(["session_date", "bracket"]).agg([
            pl.col("low_int").min().alias("b_low"),
            pl.col("high_int").max().alias("b_high")
        ])
        
        # 3. Expand to ticks
        def expand_range(row):
            return list(range(row["b_low"], row["b_high"] + self.tick_size_int, self.tick_size_int))
            
        tpo_visits = (
            brackets.with_columns(
                pl.struct(["b_low", "b_high"]).map_elements(expand_range, return_dtype=pl.List(pl.Int32)).alias("price_tick")
            )
            .explode("price_tick")
        )
        
        # 4. Count unique bracket visits per price per session
        return (
            tpo_visits.group_by(["session_date", "price_tick"]).agg(
                pl.col("bracket").n_unique().alias("tpo_count")
            ).sort(["session_date", "price_tick"])
        )

    def determine_daily_bias(self, tpo_df: pl.DataFrame) -> pl.DataFrame:
        """
        Req 2.5: Midpoint split probability (0.55/0.45).
        """
        if tpo_df.is_empty():
            return tpo_df
            
        # Group by session and calculate midpoint bias
        session_metrics = tpo_df.group_by("session_date").agg([
            pl.col("price_tick").min().alias("p_min"),
            pl.col("price_tick").max().alias("p_max"),
            pl.col("tpo_count").sum().alias("total_tpo")
        ]).with_columns(
            ((pl.col("p_min") + pl.col("p_max")) // 2).alias("midpoint")
        )
        
        # Join metrics back to calculate above/below counts
        df = tpo_df.join(session_metrics, on="session_date")
        
        bias_calc = (
            df.group_by("session_date").agg([
                (pl.col("tpo_count").filter(pl.col("price_tick") > pl.col("midpoint")).sum() / pl.col("total_tpo").first()).alias("prob_above")
            ])
            .with_columns(
                pl.when(pl.col("prob_above") >= 0.55).then(pl.lit("Bullish"))
                .when(pl.col("prob_above") <= 0.45).then(pl.lit("Bearish"))
                .otherwise(pl.lit("Neutral"))
                .alias("daily_bias")
            )
        )
        
        return tpo_df.join(bias_calc.select(["session_date", "daily_bias"]), on="session_date")

    def find_single_prints(self, tpo_df: pl.DataFrame, profile_df: pl.DataFrame, metrics: dict) -> pl.DataFrame:
        """
        Req 2.6: TPO count 1 + Volume < 0.15 V_mean.
        """
        if tpo_df.is_empty() or profile_df.is_empty():
            return tpo_df.with_columns(pl.lit(False).alias("is_single_print")).filter(False)
            
        # Join TPOs with volume profiles
        df = tpo_df.join(profile_df, on=["session_date", "price_tick"], how="left")
        
        # Criteria
        vol_threshold = 0.15 * metrics["v_mean"]
        
        return (
            df.with_columns(
                (
                    (pl.col("tpo_count") == 1) & 
                    (pl.col("volume") < vol_threshold)
                ).alias("is_single_print")
            )
            .filter(pl.col("is_single_print") == True)
        )

if __name__ == "__main__":
    from src.data.ingestion import IngestionPipeline
    from src.core.profile import VolumeProfileEngine
    import sys
    import os
    
    sys.path.append(os.getcwd())
    
    ip = IngestionPipeline()
    try:
        raw = ip.load_parquet("nq_1min_10y.parquet")
        raw = raw.head(2000)
        raw = ip.apply_integer_cast(raw)
        raw = ip.compute_session_bounds(raw)
        
        engine = VolumeProfileEngine()
        ticks = engine.interpolate_volume(raw)
        profiles = engine.build_session_profiles(ticks)
        
        struct = StructureEngine()
        tpos = struct.calculate_tpos(raw)
        tpos = struct.determine_daily_bias(tpos)
        
        day = tpos["session_date"].unique()[0]
        metrics = engine.compute_svp_metrics(day, profiles)
        
        sp = struct.find_single_prints(tpos, profiles, metrics)
        
        print(f"Daily Bias for {day}: {tpos.filter(pl.col('session_date') == day)['daily_bias'][0]}")
        print(f"Single Prints found: {len(sp)}")
        if not sp.is_empty():
            print(sp.select(["price_tick", "volume", "tpo_count"]).head(10))
    except Exception as e:
        import traceback
        traceback.print_exc()
