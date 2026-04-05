import pandas as pd
import numpy as np
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Tuple, Dict, Any

NY = ZoneInfo("America/New_York")

class DataLoader:
    def __init__(
        self,
        nq_path: str,
        es_path: str,
        start_date: str = "2014-01-02",
        end_date: str = "2026-01-30",
    ):
        self.nq_path = Path(nq_path)
        self.es_path = Path(es_path)
        self.start_date = start_date
        self.end_date = end_date

    def load_nq(self) -> pd.DataFrame:
        print("  Loading NQ parquet...")
        df = pd.read_parquet(self.nq_path, engine='pyarrow')
        # Optimized datetime handling
        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        if df['timestamp'].dt.tz is None:
            # Avoid ambiguous='infer' (slow) - assume True for local time
            df['timestamp'] = df['timestamp'].dt.tz_localize(NY, ambiguous=True)
        else:
            df['timestamp'] = df['timestamp'].dt.tz_convert(NY)
            
        df = df.set_index('timestamp').sort_index()
        df = df[~df.index.duplicated(keep='first')]
        
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = df[col].astype('float32')
        return df

    def load_es(self) -> pd.DataFrame:
        print("  Loading ES parquet...")
        df = pd.read_parquet(self.es_path, engine='pyarrow')
        # ES uses 'Date' as timestamp
        df = df.rename(columns={'Date': 'timestamp', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'})
        if 'Symbol' in df.columns:
            df = df.drop(columns=['Symbol'])
            
        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
        if df['timestamp'].dt.tz is None:
            df['timestamp'] = df['timestamp'].dt.tz_localize(NY, ambiguous=True)
        else:
            df['timestamp'] = df['timestamp'].dt.tz_convert(NY)
            
        df = df.set_index('timestamp').sort_index()
        df = df[~df.index.duplicated(keep='first')]
        
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = df[col].astype('float32')
        return df

    def get_synchronized_stream(self) -> pd.DataFrame:
        print("Synchronizing instruments...")
        nq = self.load_nq()
        es = self.load_es()
        
        print("Trimming and joining...")
        start_ts = pd.Timestamp(self.start_date, tz=NY)
        end_ts = pd.Timestamp(self.end_date, tz=NY) + pd.Timedelta(days=1, hours=-1)
        
        nq = nq.loc[start_ts:end_ts]
        es = es.loc[start_ts:end_ts]
        
        nq.columns = [f"{c}_nq" for c in nq.columns]
        es.columns = [f"{c}_es" for c in es.columns]
        
        df = pd.concat([nq, es], axis=1)
        
        df['is_synthetic_nq'] = df['close_nq'].isna()
        df['is_synthetic_es'] = df['close_es'].isna()
        df['is_synthetic'] = df['is_synthetic_nq'] | df['is_synthetic_es']
        
        df = df.ffill().bfill()
        return df
