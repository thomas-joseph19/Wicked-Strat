# STACK.md — Recommended Stack for Wicked LVN/Ledge Backtesting Engine

## Recommended Stack

| Component | Library | Version |
|-----------|---------|---------|
| Data I/O | `pandas` + `pyarrow` | pandas 2.x, pyarrow 13+ |
| Numerics | `numpy` | 1.26+ |
| Timezone | `zoneinfo` (stdlib) | Python 3.9+ |
| Charting | `plotly` | 5.x |
| ML | `xgboost` | 2.x |
| Hypertuning | `optuna` | 3.x |
| Walk-forward | Custom (see Architecture) | — |
| Market calendars | `pandas_market_calendars` | 4.x |

## Library Rationale

### pandas + pyarrow (NOT polars for this project)
While Polars is faster for pure data manipulation, this project uses **session-by-session iteration** with complex stateful logic (rolling LVN invalidation, swing registries, TPO accumulators). Pandas is better suited here because:
- Session groupby + iteration is idiomatic in pandas
- The strategy's bar-by-bar state is inherently sequential — vectorization is limited
- pyarrow handles Parquet I/O efficiently (both files < 100MB)
- The team's existing code context is pandas-based

### numpy
All hot inner loops (ATR computation, volume profile construction, swing detection) use numpy arrays directly rather than DataFrame operations. This is the critical performance layer.

### zoneinfo (NOT pytz)
`zoneinfo` is the stdlib solution since Python 3.9. It handles America/New_York DST transitions automatically and correctly. Never hardcode UTC-5 or UTC-4 offsets.

### Plotly
Best fit for per-trade HTML charts. `go.Candlestick()` + `add_hline()` for levels + `add_vrect()` for session windows. Outputs standalone HTML with embedded JavaScript — no server required.

### XGBoost + Optuna (M2)
Standard 2025 ML stack for financial time series. XGBoost's `multi:softprob` objective gives class probabilities directly. Optuna's Bayesian search outperforms grid search at the same trial budget. Set `optuna.logging.set_verbosity(optuna.logging.WARNING)` to silence console spam.

### pandas_market_calendars
Use for CME holiday calendar and early-close detection. Prevents building profiles on days with artificial volume gaps (Thanksgiving early close, etc.).

## What NOT to Use and Why

| Library | Reason to Avoid |
|---------|----------------|
| Polars | No advantage for stateful bar-by-bar session loops; adds complexity |
| Backtrader | Aging architecture; poor multi-instrument synchronization; slow |
| vectorbt | Vectorized-only; lookahead bias is extremely easy to introduce in complex multi-condition strategies |
| Nautilus Trader | Overkill; designed for live execution, not pure backtesting scripts |
| Numba | Adds JIT compilation complexity without meaningful gain at 4M rows with session iteration |
| pytz | Deprecated in favor of zoneinfo; still works but unnecessary |

## Confidence Levels

| Recommendation | Confidence | Notes |
|---------------|------------|-------|
| pandas + numpy for core loop | HIGH | Proven pattern for this complexity level |
| zoneinfo for timezone | HIGH | stdlib, no dependencies |
| plotly for charts | HIGH | Only HTML-output charting library that produces standalone files |
| XGBoost + Optuna | HIGH | Industry standard for tabular ML in finance |
| pandas_market_calendars | MEDIUM | Verify CME calendar has correct early-close dates for 2014-2026 |
| Session-by-session iteration (not vectorized) | HIGH | Vectorizing this strategy's conditions without lookahead is nearly impossible |

## Performance Notes

- At 4M rows × 2 instruments = ~8M total bars: fits comfortably in RAM as float32 (~500MB)
- Process session-by-session, not all at once: use `.groupby()` on session_id column
- Pre-compute session_id by flooring timestamp to session boundary (6PM ET)
- gc.collect() after each walk-forward window (M2 only)
- numpy arrays for ATR/volume computations, not DataFrame operations in inner loops
