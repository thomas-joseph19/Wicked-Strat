import pandas as pd
import numpy as np
from typing import Optional, Union

def compute_trueranges(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray) -> np.ndarray:
    """
    TR = max(High - Low, abs(High - PrevClose), abs(Low - PrevClose))
    """
    tr1 = highs - lows
    # PC = Previous Close
    pc = np.concatenate([[closes[0]], closes[:-1]])
    tr2 = np.abs(highs - pc)
    tr3 = np.abs(lows - pc)
    return np.maximum(tr1, np.maximum(tr2, tr3))

def compute_atr_vectorized(df: pd.DataFrame, period: int, prefix: str = "") -> pd.Series:
    """
    Vectorized ATR computation using Wilder's EMA.
    Prefix allows computing for NQ or ES (e.g. prefix='nq' for 'high_nq').
    """
    h_col = 'high' if not prefix else f'high_{prefix}'
    l_col = 'low' if not prefix else f'low_{prefix}'
    c_col = 'close' if not prefix else f'close_{prefix}'
    
    tr = compute_trueranges(df[h_col].values, df[l_col].values, df[c_col].values)
    tr_series = pd.Series(tr, index=df.index)
    
    return tr_series.ewm(alpha=1.0/period, adjust=False).mean()

def get_session_indicators(session_bars: pd.DataFrame, thresholds: any) -> pd.DataFrame:
    """
    Computes indicators for the primary instrument (NQ).
    """
    df = session_bars.copy()
    
    # ATR Computations for NQ (Primary)
    df['atr_fast'] = compute_atr_vectorized(df, thresholds.atr_period_fast, prefix='nq')
    df['atr_slow'] = compute_atr_vectorized(df, thresholds.atr_period_slow, prefix='nq')
    
    return df
