import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from src.volume_profile import VolumeProfile

@dataclass
class LVNZone:
    low: float
    high: float
    midpoint: float
    width_ticks: int
    strength: float
    session_id: str
    valid: bool = True
    invalidation_reason: Optional[str] = None
    
    # Tracking for Filter D (Consolidation)
    overlap_bars: int = 0
    midpoint_crossings: int = 0
    last_side: Optional[int] = None # -1 for below, 1 for above

class LVNDetector:
    def __init__(self, thresholds: any):
        self.thresholds = thresholds
        
    def detect_lvn_candidates(self, profile: VolumeProfile) -> List[LVNZone]:
        """
        Detects LVN zones via smoothed local minima (SVP-04, SVP-05).
        """
        if profile is None or len(profile.volumes) < 3:
            return []
            
        # 1. Smoothed Profile (D-04): 3-tick rolling average
        smoothed = np.copy(profile.volumes)
        for i in range(1, len(profile.volumes) - 1):
            smoothed[i] = (profile.volumes[i-1] + profile.volumes[i] + profile.volumes[i+1]) / 3.0
            
        # Threshold for candidate search: V_mean - 0.5 * V_std (SVP-04)
        threshold = profile.v_mean - 0.5 * profile.v_std
        
        candidates = []
        
        # 2. Local Minima Detection
        for i in range(1, len(smoothed) - 1):
            if smoothed[i] < smoothed[i-1] and smoothed[i] <= smoothed[i+1] and smoothed[i] < threshold:
                # Potential LVN center
                price = profile.get_price_at(i)
                
                # Check strength (SVP-06): 1 - (min_vol / V_mean)
                strength = 1.0 - (smoothed[i] / profile.v_mean)
                if strength < self.thresholds.lvn_strength_min:
                    continue
                    
                # Build zone: for now, it's a 1-tick midpoint. In practice, SVP-05 says merge candidates.
                # Simplified: current price level ± 0 ticks.
                candidates.append(LVNZone(
                    low=price,
                    high=price,
                    midpoint=price,
                    width_ticks=1,
                    strength=strength,
                    session_id=profile.session_id
                ))
                
        # 3. Filter A: POC Proximity (LVN-01)
        # Midpoint ± 3 ticks from current POC
        filtered = []
        poc_buffer = self.thresholds.lvn_poc_buffer_ticks * profile.tick_size
        
        for cand in candidates:
            if abs(cand.midpoint - profile.poc_price) > poc_buffer:
                filtered.append(cand)
                
        # 4. Filter C: Minimum Separation (LVN-03)
        # If within 4 ticks, keep superior strength
        if not filtered:
            return []
            
        final_candidates = []
        sep_buffer = self.thresholds.lvn_min_separation_ticks * profile.tick_size
        
        # Sort by price and then process clusters
        filtered.sort(key=lambda x: x.midpoint)
        
        for c in filtered:
            if not final_candidates:
                final_candidates.append(c)
                continue
                
            prev = final_candidates[-1]
            if c.midpoint - prev.midpoint < sep_buffer:
                # Conflict. Compare strength.
                if c.strength > prev.strength:
                    final_candidates[-1] = c
                # else: discard current
            else:
                final_candidates.append(c)
                
        return final_candidates

    def update_lvn_consolidation(self, lvn: LVNZone, bar: pd.Series):
        """
        Updates Filter D (Consolidation) status (LVN-04).
        """
        if not lvn.valid:
            return
            
        b_open = bar['open_nq']
        b_close = bar['close_nq']
        b_high = bar['high_nq']
        b_low = bar['low_nq']
        
        body_low = min(b_open, b_close)
        body_high = max(b_open, b_close)
        
        # Sub-condition 1: \u22653 bars body overlap (LVN-04.1)
        # Body (open/close min/max) overlaps LVN zone [low, high]
        if body_low <= lvn.high and body_high >= lvn.low:
            lvn.overlap_bars += 1
            if lvn.overlap_bars >= self.thresholds.lvn_consolidation_bars:
                lvn.valid = False
                lvn.invalidation_reason = f"Consolidation Override: {lvn.overlap_bars} bodies overlap"
                return
                
        # Sub-condition 2: \u22654 midpoint crossings (LVN-04.2)
        # Consecutive bars on opposite sides of midpoint
        # Current side relative to midpoint
        if b_high < lvn.midpoint:
            current_side = -1 # fully below
        elif b_low > lvn.midpoint:
            current_side = 1 # fully above
        else:
            current_side = 0 # straddling or at midpoint - doesn't count as a crossing side
            return
            
        if lvn.last_side is not None and current_side != 0 and current_side != lvn.last_side:
            lvn.midpoint_crossings += 1
            if lvn.midpoint_crossings >= self.thresholds.lvn_consolidation_crossings:
                lvn.valid = False
                lvn.invalidation_reason = f"Volatility Overflow: {lvn.midpoint_crossings} crossings"
                return
                
        if current_side != 0:
            lvn.last_side = current_side

class ConfluenceRegistry:
    """Manages multi-session LVN midpoint confluence (LVN-02, D-07)."""
    def __init__(self, num_sessions: int = 2):
        self.history: List[List[float]] = [] # List of session midpoints
        self.num_sessions = num_sessions
        
    def add_session_midpoints(self, midpoints: List[float]):
        self.history.append(midpoints)
        if len(self.history) > self.num_sessions:
            self.history.pop(0)
            
    def check_confluence(
        self,
        midpoint: float,
        tick_size: float,
        alignment_ticks: float,
        pass_if_no_prior_history: bool,
    ) -> bool:
        """Alignment within ±alignment_ticks (LVN-02); optional bootstrap when history empty."""
        if pass_if_no_prior_history and len(self.history) == 0:
            return True
        buffer = float(alignment_ticks) * tick_size
        for session_midpoints in self.history:
            for m in session_midpoints:
                if abs(midpoint - m) <= buffer:
                    return True
        return False
