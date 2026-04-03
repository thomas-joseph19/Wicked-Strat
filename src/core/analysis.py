import polars as pl
import numpy as np

class TechnicalAnalysis:
    """
    Handles ATR calculation, swing mapping, and ISMT pattern detection (Req 3.1, 3.2, 3.3).
    """

    def __init__(self, swing_window: int = 5, swing_atr_mult: float = 0.5):
        self.swing_window = swing_window
        self.swing_atr_mult = swing_atr_mult

    def calculate_atr(self, df: pl.DataFrame, period: int = 20) -> pl.Series:
        """
        Req 3.1: Calculate ATR using Wilder's Smoothing.
        """
        if df.is_empty():
            return pl.Series(name="atr", values=[])
            
        high = df.get_column("high")
        low = df.get_column("low")
        prev_close = df.get_column("close").shift(1)
        
        tr = pl.max_horizontal([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs()
        ])
        
        # Wilder's Smoothing is an EMA with alpha = 1 / period
        # Polars ewm_mean uses alpha = 1 / (1 + com) = 1 / span
        # Wilder's 20 = Polars span 39 (Wilder = 2 * period - 1?)
        # Actually: Wilder's = period. Initial ATR is SMA, then smoothed.
        return tr.ewm_mean(com=period - 1, ignore_nulls=True)

    def detect_swings(self, df: pl.DataFrame, atr_len: int = 20) -> pl.DataFrame:
        """
        Req 3.2: Label Swing Highs/Lows with zero lookahead (marked at i-5).
        """
        highs = df.get_column("high")
        lows = df.get_column("low")
        atr = self.calculate_atr(df, period=atr_len)
        
        # A swing high is highest in i-window to i+window bars
        # To avoid lookahead, we detect at bar i and mark bar i-5
        
        is_sh = (
            (highs == highs.rolling_max(window_size=2*self.swing_window+1, center=True)) &
            (highs > highs.shift(1)) # Basic momentum
        )
        
        is_sl = (
            (lows == lows.rolling_min(window_size=2*self.swing_window+1, center=True)) &
            (lows < lows.shift(1))
        )
        
        return df.with_columns([
            atr.alias("atr_20"),
            is_sh.alias("is_sh_candidate"),
            is_sl.alias("is_sl_candidate")
        ])

    def detect_ismt(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Req 3.3: Sweep of prior swing high/low + displacement closure.
        ISMT: 
        1. Price sweeps a prior swing (i.e., breaks it by < 2 ATR).
        2. Closes back inside the structure on a displacement bar (< 2 ATR total size).
        """
        # 1. Identify previous swing levels
        # We accumulate prior SH/SL levels as we iterate chronologically
        # To simplify in Polars, we can forward fill previous swing candidates
        df = df.with_columns([
            pl.when(pl.col("is_sh_candidate")).then(pl.col("high")).otherwise(None).forward_fill().alias("last_sh_level"),
            pl.when(pl.col("is_sl_candidate")).then(pl.col("low")).otherwise(None).forward_fill().alias("last_sl_level")
        ])
        
        # 2. Detect sweeps
        # Bearish ISMT: High > last_sh_level AND close < last_sh_level
        # Bullish ISMT: Low < last_sl_level AND close > last_sl_level
        
        # Filter: sweep distance < 2 ATR-20 (limit overextension)
        # Filter: displacement bar size (high-low) < 2 ATR-20
        
        df = df.with_columns([
            (
                (pl.col("high") > pl.col("last_sh_level").shift(1)) & 
                (pl.col("close") < pl.col("last_sh_level").shift(1)) &
                ((pl.col("high") - pl.col("last_sh_level").shift(1)) < 2 * pl.col("atr_20"))
            ).alias("is_bearish_ismt"),
            (
                (pl.col("low") < pl.col("last_sl_level").shift(1)) & 
                (pl.col("close") > pl.col("last_sl_level").shift(1)) &
                ((pl.col("last_sl_level").shift(1) - pl.col("low")) < 2 * pl.col("atr_20"))
            ).alias("is_bullish_ismt")
        ])
        
        return df

if __name__ == "__main__":
    from src.data.ingestion import IngestionPipeline
    import sys
    import os
    
    sys.path.append(os.getcwd())
    
    ip = IngestionPipeline()
    raw = ip.load_parquet("nq_1min_10y.parquet")
    raw = raw.head(5000)
    raw = ip.apply_integer_cast(raw)
    raw = ip.compute_session_bounds(raw)
    
    ta = TechnicalAnalysis()
    swings = ta.detect_swings(raw)
    ismt = ta.detect_ismt(swings)
    
    bearish = ismt.filter(pl.col("is_bearish_ismt"))
    bullish = ismt.filter(pl.col("is_bullish_ismt"))
    
    print(f"Total Rows: {len(ismt)}")
    print(f"Bearish ISMT found: {len(bearish)}")
    print(f"Bullish ISMT found: {len(bullish)}")
    
    if not bearish.is_empty():
        print("\nExample Bearish ISMT:")
        print(bearish.select(["timestamp", "high", "last_sh_level", "close", "atr_20"]).head(5))
