import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import List, Optional, Dict
from src.tpo import build_tpo_profile
from src.volume_profile import VolumeProfile

@dataclass
class SinglePrintZone:
    low: float
    high: float
    midpoint: float
    height_ticks: int
    session_id: str
    respected_overnight: bool = False
    inval_bar_idx: Optional[int] = None
    
def detect_single_prints(session_bars: pd.DataFrame, vp: VolumeProfile, tick_size: float = 0.25) -> List[SinglePrintZone]:
    """
    Detects Single Print zones from a session's TPO and Volume profile (SP-01 to SP-03).
    A level is SP if: TPO count == 1 AND volume < 0.15 * V_mean.
    """
    if session_bars.empty or vp is None:
        return []
        
    tpo_profile = build_tpo_profile(session_bars, tick_size)
    if not tpo_profile:
        return []
        
    sp_levels = []
    # threshold = 0.15 * V_mean (SP-02)
    vol_threshold = 0.15 * vp.v_mean
    
    # Sort prices found in TPO
    prices = sorted(tpo_profile.keys())
    for p in prices:
        tpo_count = tpo_profile[p]
        # Check volume at that level from the SVP
        v_idx = vp.get_tick_idx(p)
        vol_at_level = vp.volumes[v_idx] if 0 <= v_idx < len(vp.volumes) else 0
        
        if tpo_count == 1 and vol_at_level < vol_threshold:
            sp_levels.append(p)
            
    if not sp_levels:
        return []
        
    # Group adjacent levels into zones (SP-03)
    zones = []
    if not sp_levels:
        return []
        
    current_low = sp_levels[0]
    current_high = sp_levels[0]
    
    for i in range(1, len(sp_levels)):
        if abs(sp_levels[i] - sp_levels[i-1]) <= tick_size * 1.01: # allow for small float gap
            current_high = sp_levels[i]
        else:
            # End of zone. Check min height: 4 ticks (SP-03)
            height = round((current_high - current_low) / tick_size) + 1
            if height >= 4:
                zones.append(SinglePrintZone(
                    low=current_low,
                    high=current_high,
                    midpoint=(current_low + current_high) / 2.0,
                    height_ticks=height,
                    session_id=vp.session_id
                ))
            current_low = sp_levels[i]
            current_high = sp_levels[i]
            
    # Add last zone
    height = round((current_high - current_low) / tick_size) + 1
    if height >= 4:
        zones.append(SinglePrintZone(
            low=current_low,
            high=current_high,
            midpoint=(current_low + current_high) / 2.0,
            height_ticks=height,
            session_id=vp.session_id
        ))
        
    return zones

def update_sp_overnight_respect(zones: List[SinglePrintZone], overnight_bars: pd.DataFrame, tick_size: float = 0.25):
    """
    Checks if SP zones were respected during the overnight window (SP-04).
    Respect: approached within 2 ticks, wick into zone, NO bar body closed fully inside.
    """
    if not zones or overnight_bars.empty:
        return
        
    buffer = 2.0 * tick_size
    
    for zone in zones:
        respected = False
        zone_touched = False
        invalidated = False
        
        for _, bar in overnight_bars.iterrows():
            b_low = bar['low_nq']
            b_high = bar['high_nq']
            b_open = bar['open_nq']
            b_close = bar['close_nq']
            
            # Body range (min/max of open,close)
            body_low = min(b_open, b_close)
            body_high = max(b_open, b_close)
            
            # 1. Approach check: price approached within 2 ticks
            if b_low <= zone.high + buffer and b_high >= zone.low - buffer:
                # 2. Wick check: at least one bar's extreme touched or entered
                if b_low <= zone.high and b_high >= zone.low:
                    zone_touched = True
                    
                # 3. Invalid check: NO bar body closed FULLY inside
                # If body is entirely within [low, high]
                if body_low >= zone.low and body_high <= zone.high:
                    invalidated = True
                    break
        
        if zone_touched and not invalidated:
            # We also need to check if ANY body overlapped significantly? 
            # Requirement SP-04: "no bar body closed fully inside"
            # And "wick into the zone".
            zone.respected_overnight = True
