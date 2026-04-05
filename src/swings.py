import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import List, Optional, Tuple

@dataclass(frozen=True)
class SwingPoint:
    bar_index: int
    timestamp: pd.Timestamp
    price: float
    direction: str  # 'HIGH' or 'LOW'
    confirmed_at: int
    confirmed_time: pd.Timestamp

class SwingDetector:
    def __init__(self, lookback: int = 5, min_swing_ticks: int = 4, tick_size: float = 0.25):
        self.lookback = lookback
        self.min_ticks = min_swing_ticks
        self.tick_size = tick_size
        self.min_magnitude = min_swing_ticks * tick_size
        
        # We need a buffer of bars to check extremes
        self.highs = []
        self.lows = []
        self.times = []
        self.current_idx = -1

    def process_bar(self, timestamp: pd.Timestamp, high: float, low: float) -> List[SwingPoint]:
        """
        Process a new bar and return any swings confirmed at this bar.
        """
        self.current_idx += 1
        self.highs.append(high)
        self.lows.append(low)
        self.times.append(timestamp)
        
        swings = []
        
        # A swing at index i is confirmed at index i + lookback
        check_idx = self.current_idx - self.lookback
        
        if check_idx < self.lookback:
            return []
            
        # Check Swing High at check_idx
        # Range: [check_idx - lookback, check_idx + lookback] inclusive
        # Bar at check_idx must be the highest in the window
        window_highs = self.highs[check_idx - self.lookback : check_idx + self.lookback + 1]
        if self.highs[check_idx] == max(window_highs):
            # Check magnitude (at least one side must satisfy min_magnitude or just the extreme)
            # Strategy says "3-tick swing is NOT flagged; a 5-tick is"
            # It usually means the peak relative to immediate neighbors.
            left_neighbors = self.highs[check_idx - self.lookback : check_idx]
            right_neighbors = self.highs[check_idx + 1 : check_idx + self.lookback + 1]
            
            diff_left = self.highs[check_idx] - max(left_neighbors)
            diff_right = self.highs[check_idx] - max(right_neighbors)
            
            if min(diff_left, diff_right) >= self.min_magnitude:
                swings.append(SwingPoint(
                    bar_index=check_idx,
                    timestamp=self.times[check_idx],
                    price=self.highs[check_idx],
                    direction='HIGH',
                    confirmed_at=self.current_idx,
                    confirmed_time=timestamp
                ))
                
        # Check Swing Low at check_idx
        window_lows = self.lows[check_idx - self.lookback : check_idx + self.lookback + 1]
        if self.lows[check_idx] == min(window_lows):
            left_neighbors = self.lows[check_idx - self.lookback : check_idx]
            right_neighbors = self.lows[check_idx + 1 : check_idx + self.lookback + 1]
            
            diff_left = min(left_neighbors) - self.lows[check_idx]
            diff_right = min(right_neighbors) - self.lows[check_idx]
            
            if min(diff_left, diff_right) >= self.min_magnitude:
                swings.append(SwingPoint(
                    bar_index=check_idx,
                    timestamp=self.times[check_idx],
                    price=self.lows[check_idx],
                    direction='LOW',
                    confirmed_at=self.current_idx,
                    confirmed_time=timestamp
                ))
                
        return swings

class SwingRegistry:
    def __init__(self, buffer_size: int = 5):
        self.current_session_swings = []
        self.prior_session_tail = []
        self.buffer_size = buffer_size

    def add_swing(self, swing: SwingPoint):
        self.current_session_swings.append(swing)

    def clear_session(self):
        """Archives the last N swings to the tail and clears current session."""
        self.prior_session_tail = self.current_session_swings[-self.buffer_size:]
        self.current_session_swings = []

    def get_swings(self, direction: Optional[str] = None) -> List[SwingPoint]:
        """Returns merged tail and current swings, sorted by index."""
        all_swings = self.prior_session_tail + self.current_session_swings
        if direction:
            return [s for s in all_swings if s.direction == direction]
        return all_swings

    def get_last_n(self, n: int, direction: Optional[str] = None) -> List[SwingPoint]:
        swings = self.get_swings(direction)
        return swings[-n:]
