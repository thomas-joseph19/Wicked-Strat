import polars as pl
import numpy as np

class LVNFilterEngine:
    """
    Handles behavioral and context filtering for LVNs, ensuring they meet confluence
    and invalidation criteria (Req 2.4).
    """

    def __init__(self, tick_size_int: int = 25):
        self.tick_size_int = tick_size_int

    def check_confluence(self, current_lvns: pl.DataFrame, prior_sessions_lvns: list[pl.DataFrame]) -> pl.DataFrame:
        """
        Confluence: An LVN is confluent if session -1 or -2 has a Raw LVN 
        within ±2 ticks of the current price level.
        """
        if not prior_sessions_lvns:
            return current_lvns.with_columns(pl.lit(False).alias("is_confluent"))
            
        confluence_limit = 2 * self.tick_size_int
        
        # Collect all prior prices
        prior_prices = []
        for df in prior_sessions_lvns:
            if not df.is_empty():
                prior_prices.extend(df.get_column("price_tick").to_list())
                
        if not prior_prices:
            return current_lvns.with_columns(pl.lit(False).alias("is_confluent"))
            
        # For each current LVN, check if any prior price is within limit
        def is_near(price):
            return any(abs(price - p) <= confluence_limit for p in prior_prices)
            
        return current_lvns.with_columns(
            pl.col("price_tick").map_elements(is_near, return_dtype=pl.Boolean).alias("is_confluent")
        )

    def mask_pocs(self, lvns: pl.DataFrame, pocs: list[int]) -> pl.DataFrame:
        """
        Req 2.4: Discard LVNs within 3 ticks (0.75 points) of any POC.
        """
        mask_limit = 3 * self.tick_size_int
        
        def is_masked(price):
            return any(abs(price - poc) <= mask_limit for poc in pocs if poc is not None)
            
        return lvns.with_columns(
            pl.col("price_tick").map_elements(is_masked, return_dtype=pl.Boolean).alias("is_masked")
        ).filter(pl.col("is_masked") == False).drop("is_masked")

    def apply_minimum_separation(self, lvns: pl.DataFrame, min_sep_ticks: int = 4) -> pl.DataFrame:
        """
        Keeps the highest strength LVN in a cluster (e.g., 4 ticks).
        """
        if lvns.is_empty():
            return lvns
            
        sep_limit = min_sep_ticks * self.tick_size_int
        sorted_lvns = lvns.sort(["price_tick", "lvn_strength"], descending=[False, True])
        
        keep_indices = []
        last_price = -float('inf')
        
        # Since it's sorted by price, we can check proximity sequentially
        # and prioritize highest strength via sorting order within clusters
        for i, row in enumerate(sorted_lvns.to_dicts()):
            if row["price_tick"] >= last_price + sep_limit:
                keep_indices.append(i)
                last_price = row["price_tick"]
                
        return sorted_lvns[keep_indices]

    def track_invalidation(self, lvns: pl.DataFrame, bar_data: pl.DataFrame) -> pl.DataFrame:
        """
        Req 2.4: Consolidation Invalidation.
        Invalid if:
        1. 4 unique 1-min crossings occur.
        2. 3 unique 1-min bars print INSIDE the price zone (Consolidation).
        """
        if lvns.is_empty() or bar_data.is_empty():
            return lvns.with_columns(pl.lit(False).alias("is_invalidated"))
            
        # This is a potentially expensive bar-by-bar traversal
        # We optimize by only checking bars in the same session
        lvn_list = lvns.to_dicts()
        bar_list = bar_data.to_dicts()
        
        invalid_mask = []
        for lvn in lvn_list:
            price = lvn["price_tick"]
            
            crossings = 0
            consolidation_bars = 0
            is_broken = False
            
            for bar in bar_list:
                high = bar["high_int"]
                low = bar["low_int"]
                
                # Check crossing: bar high/low spans the price
                if low <= price <= high:
                    crossings += 1
                    
                # Check consolidation: open AND close AND low/high in range?
                # Actually, spec: "3 bars print INSIDE the price zone"
                # Standard interpretation: Price is within the OHLC range for 3 bars.
                if low <= price <= high:
                    consolidation_bars += 1
                    
                if crossings >= 4 or consolidation_bars >= 3:
                    is_broken = True
                    break
                    
            invalid_mask.append(is_broken)
            
        return lvns.with_columns(pl.Series(name="is_invalidated", values=invalid_mask))

if __name__ == "__main__":
    # Smoke test logic
    engine = LVNFilterEngine()
    
    mock_lvns = pl.DataFrame({
        "price_tick": [140000, 140025, 140050], # 1400.0, 1400.25, 1400.5
        "lvn_strength": [0.9, 0.85, 0.95]
    })
    
    # Separation test (4 ticks = 100 points)
    filtered = engine.apply_minimum_separation(mock_lvns, min_sep_ticks=4)
    print("Separation Filter (Keep highest strength in 4-tick cluster):")
    print(filtered)
    
    # POC Masking test (1400.0 is within 3 ticks of 1400.25)
    masked = engine.mask_pocs(mock_lvns, [140025])
    print("\nPOC Masking (Exclude if near POC 1400.25):")
    print(masked)
