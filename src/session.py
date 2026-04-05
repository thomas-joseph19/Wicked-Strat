from datetime import datetime, timedelta, time
import pandas as pd
import numpy as np
from zoneinfo import ZoneInfo
from typing import List, Tuple, Optional

NY = ZoneInfo("America/New_York")

def get_session_id(dt: datetime) -> str:
    """
    Implements 24-hour Globex session boundary (6:00 PM ET cutoff).
    Bars starting at 18:00 ET belong to the NEXT day's session.
    """
    cutoff = dt.replace(hour=18, minute=0, second=0, microsecond=0)
    if dt >= cutoff:
        session_dt = dt + timedelta(days=1)
    else:
        session_dt = dt
    return session_dt.date().isoformat()

class SessionManager:
    def __init__(self, full_stream: pd.DataFrame):
        """
        Input DF must have a DateTimeIndex localized to America/New_York.
        """
        self.df = full_stream
        if not hasattr(self.df.index, 'hour'):
             raise ValueError("DataFrame index must be a DateTimeIndex")
             
        # MAX performance: vectorized floor to session day.
        # This is instant on 4M+ rows.
        self.df['session_id'] = (self.df.index + pd.Timedelta(hours=6)).floor('D')
        
        # Keep as Timestamp objects which are highly optimized in pandas
        self.sessions = list(self.df['session_id'].unique())
        self.sessions.sort()

    def get_session(self, session_id: any) -> pd.DataFrame:
        """Returns the full 24-hour bar set for a specific session."""
        return self.df[self.df['session_id'] == session_id]

    @staticmethod
    def get_rth_bars(session_bars: pd.DataFrame) -> pd.DataFrame:
        """Returns Regular Trading Hours bars (9:30 AM -> 4:00 PM ET)."""
        idx = session_bars.index
        return session_bars[(idx.time >= time(9, 30)) & (idx.time <= time(16, 0))]

    @staticmethod
    def get_pre_market_bars(session_bars: pd.DataFrame) -> pd.DataFrame:
        """Returns bars from prior 18:00 until 09:29 AM ET."""
        idx = session_bars.index
        return session_bars[idx.time < time(9, 30)]

class WindowConfig:
    RTH_OPEN = time(9, 30)
    RTH_CLOSE = time(16, 0)
    EOD_CUTOFF = time(15, 45)
    # RTH aggressive ledge: Phase 4 ROADMAP success #5 — 09:28 rejected, 09:32 accepted
    AGGRESSIVE_START = time(9, 30)
    AGGRESSIVE_END = time(10, 0)
    PRE_RTH_CUTOFF = time(9, 29)
