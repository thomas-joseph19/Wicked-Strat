import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional

@dataclass
class VolumeProfile:
    session_id: str
    tick_size: float
    base_price: float
    volumes: np.ndarray  # raw volume per tick
    
    # Computed stats
    v_mean: float = 0.0
    v_std: float = 0.0
    v_total: float = 0.0
    poc_price: float = 0.0
    vah_price: float = 0.0
    val_price: float = 0.0
    
    def get_tick_idx(self, price: float) -> int:
        return int(round((price - self.base_price) / self.tick_size))

    def get_price_at(self, idx: int) -> float:
        return self.base_price + idx * self.tick_size

    def compute_stats(self):
        """Computes V_mean, V_std, POC, VAH, VAL (SVP-03)."""
        valid_vols = self.volumes[self.volumes > 0]
        if len(valid_vols) == 0:
            return
            
        self.v_total = np.sum(self.volumes)
        self.v_mean = np.mean(valid_vols)
        self.v_std = np.std(valid_vols)
        
        # POC: Price with maximum volume
        poc_idx = np.argmax(self.volumes)
        self.poc_price = self.get_price_at(poc_idx)
        
        # VAH / VAL (70% Value Area)
        target_vol = 0.70 * self.v_total
        current_vol = self.volumes[poc_idx]
        low_idx = poc_idx
        high_idx = poc_idx
        
        while current_vol < target_vol:
            # Check expansion below and above
            # Standard VA algorithm: expand by 2 ticks in direction with more volume
            # Simplified for now: expand in direction of higher volume
            prev_low_vol = self.volumes[low_idx-1] if low_idx > 0 else 0
            prev_high_vol = self.volumes[high_idx+1] if high_idx < len(self.volumes)-1 else 0
            
            if prev_low_vol >= prev_high_vol and low_idx > 0:
                current_vol += prev_low_vol
                low_idx -= 1
            elif high_idx < len(self.volumes)-1:
                current_vol += prev_high_vol
                high_idx += 1
            else:
                break
                
        self.val_price = self.get_price_at(low_idx)
        self.vah_price = self.get_price_at(high_idx)

def build_volume_profile(session_id: str, bars: pd.DataFrame, tick_size: float = 0.25) -> VolumeProfile:
    """
    Builds a VolumeProfile for a session (SVP-01, CORE-03).
    Pre-allocates numpy array (D-01, D-02).
    """
    if bars.empty:
        return None
        
    s_low = bars['low_nq'].min()
    s_high = bars['high_nq'].max()
    
    # Pre-allocate according to D-02: session range +/- 50 pts
    base_price = s_low - 50.0
    max_price = s_high + 50.0
    num_ticks = int(round((max_price - base_price) / tick_size)) + 1
    
    volumes = np.zeros(num_ticks, dtype=np.float32)
    profile = VolumeProfile(session_id, tick_size, base_price, volumes)
    
    for _, bar in bars.iterrows():
        b_low = bar['low_nq']
        b_high = bar['high_nq']
        b_vol = bar['volume_nq']
        
        if b_vol <= 0:
            continue
            
        # Distribute volume uniformly across all ticks in the bar range (CORE-03)
        low_idx = profile.get_tick_idx(b_low)
        high_idx = profile.get_tick_idx(b_high)
        num_bar_ticks = high_idx - low_idx + 1
        
        vol_per_tick = b_vol / num_bar_ticks
        volumes[low_idx : high_idx + 1] += vol_per_tick
        
    profile.compute_stats()
    return profile
