# PLAN: Phase 2 — Swing Detection & TPO Bias Engine

## Objective
Implement a hindsight-free swing high/low detection system with a cross-session registry and a pre-market TPO bias calculation engine. Both systems must be lookahead-free and anchored to the 18:00 ET Globex session boundary.

## Requirements Addressed
- **SWING-01**: Asymmetric swing high detection (confirmed at `i+lookback`).
- **SWING-02**: Asymmetric swing low detection.
- **SWING-03**: Minimum swing magnitude (4 ticks).
- **SWING-04**: `confirmed_at` tracking in registry.
- **SWING-05**: Reproducibility (byte-identical output).
- **TPO-01**: 30-minute bar TPO profile from pre-RTH bars.
- **TPO-02**: TPO letter count per price level (tick-level).
- **TPO-03**: Bias rules (55%/45% thresholds).
- **TPO-04**: Skip neutral sessions (logic gate).
- **TPO-05**: Bias locked at 9:30 AM.

## Wave 1: Swing Detection Engine
### Task 1: Implement `src/swings.py`
- **Action**: Implement `detect_swings_incremental` that checks if the bar at `current_index - lookback` is a local extreme.
- **Read First**: `.planning/research/PITFALLS.md` (P2 Symmetric Swing Lookahead), `src/config.py`.
- **Acceptance Criteria**:
  - `SwingDetector(lookback=5).process_bar(bars[10])` only returns a swing found at index 5.
  - Swings below 4 ticks are rejected (SWING-03).

### Task 2: Implement `SwingRegistry`
- **Action**: Create a registry that holds `current_session_swings` and `prior_session_tail` (frozen last 5 from prior session). Implement a query method to get the latest N confirmed swings.
- **Read First**: `.planning/phases/02-swing-detection-tpo-bias-engine/02-CONTEXT.md` (D-01, D-02).
- **Acceptance Criteria**:
  - `registry.clear_session()` populates the tail from current before clearing.
  - `registry.get_last_n(2)` returns correct swings across the session boundary.

## Wave 2: TPO Bias Engine
### Task 1: Implement `src/tpo.py`
- **Action**: Implement `compute_tpo_bias` that resamples pre-RTH bars into 30-min buckets anchored at 18:00 ET. Group by 0.25 tick point buckets.
- **Read First**: `.planning/research/PITFALLS.md` (P6 Resample), `src/session.py`.
- **Acceptance Criteria**:
  - `compute_tpo_bias(pre_rth_bars)` returns `BULLISH` for a sample with heavy upper distribution.
  - Resample uses `origin='session_start_18h'`, `label='left'`, `closed='left'`.

## Wave 3: Integration & Smoke Test
### Task 1: Update `main.py`
- **Action**: Add swing and TPO bias display to the Phase 1 smoke test loop. 
- **Acceptance Criteria**:
  - `python main.py --mode backtest` prints TPO Bias for each session.
  - Prints the count of swings detected in the session.

## Verification for Phase 2
- **V-01**: Swing `confirmed_at` check (delay verification).
- **V-02**: TPO Resample boundary check (anchored at 18:00).
- **V-03**: NQ Tick-level TPO granularity (0.25 pt).
- **V-04**: Neutral session detection.

## Must-Haves (Goal Check)
- [ ] Swing high/low detection is hindsight-free (delayed confirmation).
- [ ] TPO bias is locked at 9:30 AM using overnight data.
- [ ] Swing registry persists a tail from the prior session.
- [ ] TPO aggregation uses correct pandas boundary settings.
