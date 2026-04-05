# PITFALLS.md — Critical Bugs and Failure Modes

## Critical Bugs (Silent Failures)

These produce incorrect results without obvious errors. The backtest "works" but the P&L is wrong.

### P1 — Volume Profile Lookahead Bias
**The Bug**: Computing LVNs using volume data from the full trading day (including post-9:30 PM volume) when making pre-RTH decisions.
**Symptom**: Strategy appears to enter at perfect LVN levels that couldn't have been known at trade time.
**Fix**: Build the SVP using ONLY bars with `timestamp < 09:30 ET`. The profile grows from the pre-market, not the full day.
**Phase**: Phase 3 (Volume Profile)

### P2 — Symmetric Swing Detection (Most Common Lookahead in Practice)
**The Bug**: `argmax(highs[i-5:i+5])` — the right half of that window is the future when evaluated at bar `i`.
**Symptom**: Excellent backtest P&L that collapses the moment you add a 1-bar delay to signal generation.
**Fix**: Use asymmetric confirmation: swing high at index `i` is confirmed only when bars `i+1` through `i+5` all print lower highs. This is only known at bar `i+5`, not at bar `i`.
**Phase**: Phase 2 (Swing Detection)

### P3 — Entry on Intra-Bar Signal
**The Bug**: Checking if an ISMT pattern is forming before the bar that triggers it has closed.
**Symptom**: Entries at prices that were never possible on a closed bar.
**Fix**: All signal evaluation happens AFTER `bar.close` is known. Never evaluate signals mid-bar.
**Phase**: Phase 4 (Signal Generation)

### P4 — Short Trade P&L Polarity
**The Bug**: Using `(exit_price - entry_price)` for shorts instead of `(entry_price - exit_price)`.
**Symptom**: Short trades show as losses when they should be wins, or worse — losses show as large wins.
**Fix**: 
```python
if direction == 'LONG':
    gross_pnl = (exit_price - entry_price) * contracts * point_value
elif direction == 'SHORT':
    gross_pnl = (entry_price - exit_price) * contracts * point_value
```
**Phase**: Phase 5 (Execution Engine)

### P5 — LVN Carry-Over Across Sessions
**The Bug**: Keeping LVN zone objects from session N and using them in session N+1 without recomputing.
**Symptom**: Entries at LVN levels that no longer exist in the current session's volume profile.
**Fix**: At every session boundary (6 PM ET), clear ALL active LVNs and rebuild from the new session's profile. Never carry LVNs across sessions.
**Phase**: Phase 3 (LVN Management)

### P6 — pandas resample() Label Lookahead
**The Bug**: `df.resample('30min').agg(...)` with default `label='left'` but wrong OHLC logic, or forgetting to specify `closed='left'`.
**Symptom**: 30-min bars have slightly wrong highs/lows because the aggregation boundary is shifted.
**Fix**: 
```python
df.resample('30min', label='left', closed='left').agg({
    'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
})
```
**Phase**: Phase 1 (Data Infrastructure)

### P7 — SMT False Signal on Synthetic Bars
**The Bug**: Forward-filling missing ES bars, then computing SMT divergence between NQ (real) and ES (synthetic).
**Symptom**: SMT signals fire at times when ES had no actual trading activity — the "divergence" is just a data gap.
**Fix**: Mark synthesized bars with `is_synthetic=True`. Skip SMT computation for any bar pair where either instrument's bar is synthetic.
**Phase**: Phase 4 (SMT Detection)

### P8 — Drawdown from Fixed Base
**The Bug**: Computing max drawdown as `(equity - starting_equity) / starting_equity` without tracking the rolling peak.
**Symptom**: Drawdown resets to zero every time equity recovers to the starting level.
**Fix**: `peak = equity_curve.expanding().max(); drawdown = (equity_curve - peak) / peak`
**Phase**: Phase 6 (Metrics)

---

## Common Bugs (Visible Failures)

These usually produce obvious errors or wildly incorrect numbers.

### C1 — DST Timezone Shift
**Symptom**: Session starts at 10:30 AM or 8:30 AM on certain days twice a year.
**Fix**: Never hardcode UTC offset. Use `zoneinfo.ZoneInfo("America/New_York")` exclusively.
**Phase**: Phase 1

### C2 — Position Sizing Divide by Zero
**Symptom**: `ZeroDivisionError` or `inf` contracts on flat or gap bars.
**Fix**: `if abs(entry_price - stop_price) < tick_size: skip_setup; if atr_5 == 0: use_fallback_atr`
**Phase**: Phase 5

### C3 — Commission Double-Counting
**Symptom**: Net P&L is much lower than gross P&L by 2× expected commission drag.
**Fix**: `net_pnl = gross_pnl - (contracts * commission_per_side * 2)`. The 2× is for one entry leg + one exit leg.
**Phase**: Phase 5

### C4 — Partial Exit Commission Under-Counting
**Symptom**: 60%/40% split trades show slightly higher net P&L than they should.
**Fix**: Each partial exit event is a separate round-trip exit leg. Charge commission on each:
- TP1: `exit_size_1 * commission_per_side` 
- TP2: `exit_size_2 * commission_per_side`
- Entry already charged on open: `full_size * commission_per_side`
**Phase**: Phase 5

### C5 — Monte Carlo Price Gap (M2)
**Symptom**: ATR reads as 10,000+ points in MC simulations; no signals found.
**Cause**: Stitching 2014-era NQ bars (~4,000) with 2024-era NQ bars (~18,000) without normalization.
**Fix**: Day-by-day offset normalization in StochasticTapeGenerator — each day's open is shifted to match prior day's close before applying jitter.
**Phase**: Phase 11/12 (M2)

### C6 — MC State Mutation Between Paths
**Symptom**: Second MC path "remembers" LVN levels from first path; signals based on stale state.
**Fix**: All session-level state (LVN zones, swing registries, SP zones, position) must be re-initialized to empty at the start of each MC path and each session within a path.
**Phase**: Phase 11 (M2)

### C7 — RR Divide by Zero
**Symptom**: `ZeroDivisionError` or `inf` RR values in trade log.
**Fix**: `if entry_price == stop_price: skip_setup` — also guard with `if risk <= 0: skip_setup`
**Phase**: Phase 5

### C8 — Profit Factor Infinity
**Symptom**: Profit Factor shows `inf` when there are no losing trades (common in small test windows).
**Fix**: `pf = gross_wins / gross_losses if gross_losses > 0 else gross_wins`
**Phase**: Phase 6

---

## Performance Pitfalls

### PERF1 — Dictionary-Based Profile Lookups at Scale
**Problem**: `profile[price]` in a Python dict for every bar in a 4M-row dataset.
**Fix**: Build numpy arrays indexed by tick number (`tick_idx = round(price / tick_size)`). O(1) array lookup vs O(1) average dict but much better cache performance.

### PERF2 — Memory Overflow on 12-Year Dataset
**Problem**: Loading both parquet files into memory as float64 DataFrames = ~1.5GB each.
**Fix**: Load as float32 where possible. Process session-by-session rather than all at once.

### PERF3 — Walk-Forward Memory Leak (M2)
**Problem**: After each walk-forward window, training DataFrames and models remain in memory.
**Fix**: 
```python
del train_df, train_x, train_y, model
gc.collect()
```
After every window. 17 years × unmanaged DataFrames = crash.

### PERF4 — Per-Bar Swing Recalculation
**Problem**: Re-running swing detection on the entire session history for each new bar.
**Fix**: Use incremental detection — only check if the bar `N-lookback` bars ago qualifies as a new swing. Maintain a registry of confirmed swings.

---

## Phase Mapping

| Phase | Pitfalls Addressed |
|-------|--------------------|
| Phase 1: Data Infrastructure | P6 (resample), C1 (DST), C5 context |
| Phase 2: Swing Detection | P2 (symmetric swing), swing registry design |
| Phase 3: Volume Profile + LVN | P1 (VP lookahead), P5 (LVN carry-over) |
| Phase 4: Signal Generation | P3 (intra-bar entry), P7 (SMT synthetic), P2 (swing confirmation) |
| Phase 5: Execution Engine | P4 (short polarity), C2 (sizing), C3/C4 (commission), C7/C8 (guards) |
| Phase 6: Metrics | P8 (drawdown), C8 (profit factor) |
| Phase 7: Audit | All of the above — reproducibility gate catches silent failures |
| Phase 11-12 (M2) | C5 (MC normalization), C6 (state mutation), PERF3 (memory) |
