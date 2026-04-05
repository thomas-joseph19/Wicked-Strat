# Phase 1 Research: Data Infrastructure & Core Candle Math

## 1. Technical Research

### 1.1. Data Loading & Normalization
- **ES Schema**: `Date`, `Symbol`, `Open`, `High`, `Low`, `Close`, `Volume`.
- **NQ Schema**: `open`, `high`, `low`, `close`, `volume`, `timestamp`.
- **Unified Schema**: `timestamp`, `open`, `high`, `low`, `close`, `volume`.
- **Optimization**: Use `pyarrow` engine for `read_parquet`. For 4M-8M rows, it takes < 2 seconds.
- **Normalization**: To normalize NQ columns to lowercase and rename `Date` to `timestamp` for ES. Convert `timestamp` to `datetime64[ns, America/New_York]` immediately.

### 1.2. Session Boundary (24h Globex)
- 6 PM ET prior day → 6 PM ET current day.
- Pattern:
  ```python
  def get_session_id(ts):
      if ts.hour >= 18:
          return (ts + timedelta(days=1)).date()
      return ts.date()
  ```
- This satisfies DATA-02 and session grouping.

### 1.3. Synchronized Dual-Instrument Stream
- NQ and ES bars are both available for each minute.
- Use `outer join` on `timestamp` floors to 1-min.
- Forward-fill missing values (`method='ffill'`).
- Add `is_synthetic` column for filled bars (DATA-04).
- NQ is the primary instrument, ES is signal confluence only.

### 1.4. Core Math (ATR)
- `DATA-CORE-01`: `bars[0:i+1]` only.
- ATR_5 and ATR_20 using standard Wilder's/EMA pattern for True Range.
- Avoid P2 (Lookahead): The function MUST be implemented to only access prior bars or provide an incremental update method.
- Performance: Vectorized ATR for the full history is safe since it's just a time-series computation, but the execution loop must only see `ATR[session_bar_index]`.

### 1.5. Config System
- YAML config for StrategyThresholds and InstrumentConfig.
- Use Python `dataclass(frozen=True)` for consumption (D-07, D-08).

## 2. Validation Architecture (Nyquist)

| Dimension | Rule | Implementation in Phase 1 |
|-----------|------|---------------------------|
| **1. Ground Truth** | Source of truth for bar data | Read directly from parquet, verified by sample inspect. |
| **2. Time Sync** | Same minute for both symbols | Outer join on 1min timestamp floors. |
| **3. Lookahead** | No access at index `i` to `i+1` | Session-by-session iteration loop. |
| **4. Reproducibility** | Same bars on every run | Deterministic loading and schema transformation. |
| **5. Continuity** | Gap filling | Forward-fill synthetic bars + `is_synthetic` flag. |
| **6. Session Clarity** | 6 PM cutoff correctness | Explicit session_id assignment. |
| **7. Performance** | Efficient memory usage | float32 casting where safe. |
| **8. Hindsight-Free** | ATR compute uses only past | Standard TR/EMA loop. |

## 3. Module Stubs
Create stubs for all 15 modules listed in `01-CONTEXT.md` with `NotImplementedError`. This creates the import graph.
