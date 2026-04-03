# Research Summary: Wicked LVN/Ledge Strategy

## Context
Automated mechanical implementation of an advanced order-flow, structure, and acceptance strategy focusing on non-hindsight 1-min charting validation and execution.

## Key Findings

### Stack Dynamics
Python + Polars + VectorBT (or custom Numba loops). The standard stack relies on rapid vectorization because traditional iterative loops over 10 years of 1-min data (approx 3.4M rows assuming only regular market days, but ~5.2M considering globex) will be too slow, especially for TPO and local profile slice generation. Polars is strongly recommended for its native multithreading and fast grouping abilities. If iterating sequentially for the simulated backtest engine, a Numba JIT-compiled loop is optimal to maintain sub-minute performance.

### Essential Features
- **SVP Algorithms**: Multi-day state preservation is critical. Moving session bounds (6 PM to 6 PM) over an uninterrupted 10-year array requires precise timezone-aware windowing.
- **ISMT Engine**: Swing logic with configurable lookbacks properly filtered by variable ATR to prevent micro noise.
- **Single Print Tracking**: Fast gap detection across consecutive 30-min price buckets.
- **Execution Simulator**: Stop-loss and risk:reward evaluation must be natively implemented independent of the indicators to avoid look-ahead bias and order execution flaws.

### Architecture
- `data_handler`: Ingests `nq_1min_10y.parquet`, standardizes timestamps, normalizes ticks.
- `profile_engine`: Holds logic for SVPs, TPOs, POC, Val Areas, LVN detection.
- `signal_generator`: Detects Swings, ISMT, LVN touches and Single print confluence points.
- `simulator`: Processes entry rules chronologically, handles RR logic, Risk/Reward updates, max stop loss calculations, and generates PnL.

### Critical Pitfalls
- **Hindsight Bias in Volume Profile**: Calculating a 24h SVP, but querying its final state *before* the 24h period finishes, leading to future-peeking. Profiles must be built cumulatively up to the current bar, or computed daily but only utilized for the *following* session, or strictly windowed. The strategy specs state it computes at 6PM to 9:30AM but we update real-time with LVN digestion, meaning the profile logic must be fully unrolled on a rolling cumulative basis.
- **Tick Discretization Errors**: 0.25 tick sizes on floats can lead to floating-point rounding errors when hashing price levels. Must use integer math (e.g., price * 100) internally.
- **Order Slippage/Fill Assumptions**: LVNs are tight 1-4 tick zones – entering exactly at these zones can mean missed executions. The backtest simulator logic needs a conservative fill assumption (limit order touched but not breached might not fill).

[End Summary]
