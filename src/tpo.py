import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
from enum import Enum

class Bias(Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"

def build_tpo_profile(bars: pd.DataFrame, tick_size: float = 0.25, prefix: str = 'nq') -> Dict[float, int]:
    """
    Builds a TPO profile at tick-level granularity (TPO-01, D-04).
    Every 30-min period visiting a price level gets a TPO count.
    """
    if bars.empty:
        return {}
        
    h_col = f'high_{prefix}'
    l_col = f'low_{prefix}'
    
    # Anchor to 18:00 ET always (D-06)
    # Using floor('D') - 6h might be tricky. 
    # Use session_start directly if available or assume 18:00 relative to first bar.
    first_ts = bars.index[0]
    # Anchor at 18:00 ET prior or current day based on Globex rules.
    # Safe anchor: first_ts.replace(hour=18, minute=0, ...) logic
    if first_ts.hour >= 18:
        origin = first_ts.replace(hour=18, minute=0, second=0, microsecond=0)
    else:
        origin = (first_ts - pd.Timedelta(days=1)).replace(hour=18, minute=0, second=0, microsecond=0)
        
    # Group into 30-min buckets
    tpo_bars = bars.resample('30min', label='left', closed='left', origin=origin).agg({
        h_col: 'max',
        l_col: 'min'
    }).dropna()
    
    tpo_counts: Dict[float, int] = {}
    for _, bar in tpo_bars.iterrows():
        b_low = bar[l_col]
        b_high = bar[h_col]
        
        ticks = np.arange(round(b_low/tick_size), round(b_high/tick_size) + 1) * tick_size
        for t in ticks:
            # Round for floating point stability
            t_key = round(t / tick_size) * tick_size
            tpo_counts[t_key] = tpo_counts.get(t_key, 0) + 1
            
    return tpo_counts

def compute_tpo_bias(pre_rth_bars: pd.DataFrame, tick_size: float = 0.25) -> Tuple[Bias, float]:
    """
    Locked at 09:30 AM ET based on pre-RTH 30-min bar aggregation (TPO-01, TPO-03).
    """
    if pre_rth_bars.empty:
        return Bias.NEUTRAL, 0.5
        
    profile = build_tpo_profile(pre_rth_bars, tick_size)
    if not profile:
        return Bias.NEUTRAL, 0.5
        
    prices = list(profile.keys())
    sess_high = max(prices)
    sess_low = min(prices)
    midpoint = (sess_high + sess_low) / 2.0
    
    upper_tpos = 0
    lower_tpos = 0
    
    for price, count in profile.items():
        if price > midpoint:
            upper_tpos += count
        elif price < midpoint:
            lower_tpos += count
            
    total_tpos = upper_tpos + lower_tpos
    if total_tpos == 0:
        return Bias.NEUTRAL, 0.5
        
    upper_ratio = upper_tpos / total_tpos
    
    if upper_ratio > 0.55:
        return Bias.BULLISH, upper_ratio
    elif upper_ratio < 0.45:
        return Bias.BEARISH, upper_ratio
    else:
        return Bias.NEUTRAL, upper_ratio
