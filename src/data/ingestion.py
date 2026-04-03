import polars as pl
import pandas as pd
from datetime import datetime, time
import pytz

class IngestionPipeline:
    """
    Handles loading, normalizing, and session-binding for NQ 1-min OHLCV data.
    """
    
    def __init__(self, timezone: str = "America/New_York"):
        self.tz = pytz.timezone(timezone)
        
    def load_parquet(self, path: str) -> pl.DataFrame:
        """
        Loads the parquet file into a Polars DataFrame and ensures timezone awareness.
        """
        df = pl.read_parquet(path)
        
        # Ensure timestamp is datetime type and localized
        if df["timestamp"].dtype == pl.Int64:
            # Assume microseconds if large integer
            df = df.with_columns(pl.from_epoch("timestamp", time_unit="us"))
            
        # Localize to Eastern Time
        # The parquet might be in UTC or naive. Standardizing to America/New_York.
        df = df.with_columns(
            pl.col("timestamp").dt.replace_time_zone("UTC").dt.convert_time_zone(self.tz.zone)
        )
        
        return df

    def apply_integer_cast(self, df: pl.DataFrame, multiplier: int = 100) -> pl.DataFrame:
        """
        Casts price columns to integers using a multiplier to avoid floating point errors
        for tick-level calculations (0.25 tick size).
        """
        price_cols = ["open", "high", "low", "close"]
        
        new_cols = [
            (pl.col(col) * multiplier).cast(pl.Int32).alias(f"{col}_int")
            for col in price_cols
        ]
        
        return df.with_columns(new_cols)

    def compute_session_bounds(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Calculates the session_date based on the 6:00 PM ET session start.
        If time >= 18:00, it belongs to the next calendar day's session.
        """
        # Logic: session_date = timestamp.date + 1 day IF time >= 18:00
        return df.with_columns(
            pl.when(pl.col("timestamp").dt.hour() >= 18)
            .then(pl.col("timestamp").dt.date().dt.offset_by("1d"))
            .otherwise(pl.col("timestamp").dt.date())
            .alias("session_date")
        )

if __name__ == "__main__":
    # Quick sanity check
    pipeline = IngestionPipeline()
    try:
        data = pipeline.load_parquet("nq_1min_10y.parquet")
        data = pipeline.apply_integer_cast(data)
        data = pipeline.compute_session_bounds(data)
        print("Data loaded and processed successfully.")
        print(data.head())
        print(data.select(["timestamp", "session_date"]).head(20))
    except Exception as e:
        print(f"Error checking data: {e}")
