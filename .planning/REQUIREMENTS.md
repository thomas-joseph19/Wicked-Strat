# REQUIREMENTS.md — Wicked LVN/Ledge Strategy Backtest Engine

> Requirements follow `[CATEGORY]-[NUMBER]` format. All M1 requirements are in scope for V1.

---

## V1 Requirements (Milestone 1 — Mechanical Backtest Engine)

### Data Infrastructure (DATA)

- [ ] **DATA-01**: System loads ES parquet (`1Min_ES.parquet`) and NQ parquet (`nq_1min_10y.parquet`) and normalizes both to a unified schema: `{timestamp (ET datetime), open, high, low, close, volume, session_id}`
- [ ] **DATA-02**: System assigns `session_id` to each bar using 24-hour Globex boundary (6:00 PM ET prior day → 6:00 PM ET current day)
- [ ] **DATA-03**: System handles DST transitions using `zoneinfo.ZoneInfo("America/New_York")` — no hardcoded UTC offsets
- [ ] **DATA-04**: System builds a synchronized dual-instrument bar stream where each minute index has both NQ and ES bars (forward-fill missing bars, mark synthetic bars with `is_synthetic=True`)
- [ ] **DATA-05**: System defines `InstrumentConfig` with tick size (0.25), point value (NQ=$20, ES=$50), and commission per side
- [ ] **DATA-06**: System defines `StrategyThresholds` config object containing all tunable parameters (see parameter table in specification)
- [ ] **DATA-07**: Backtest window is 2014-01-02 → 2026-01-30 (ES dataset boundary); NQ data is trimmed to match

### Core Math (CORE)

- [ ] **CORE-01**: `compute_atr(bars, period)` computes True Range and ATR for periods 5 and 20, using only `bars[0:i+1]` — no future data
- [ ] **CORE-02**: All math functions accept only `data[i-N:i]` slices — no `data[i+1]` access anywhere in the codebase
- [ ] **CORE-03**: Volume distribution: for each 1-min bar, distribute volume uniformly across all price ticks from low to high

### Session Volume Profile (SVP)

- [ ] **SVP-01**: `build_volume_profile(session_bars)` produces `{price_level: volume}` dict for all bars in a session
- [ ] **SVP-02**: Profile is frozen at 9:30 AM ET using only pre-RTH bars — NOT rebuilt during RTH bar-by-bar loop
- [ ] **SVP-03**: System computes V_mean, V_std, V_total, POC, VAH, VAL from the frozen profile
- [ ] **SVP-04**: LVN detection: apply 3-tick rolling average smoothing, then detect local minima below `V_mean - 0.5 * V_std`
- [ ] **SVP-05**: Adjacent LVN candidates are merged into zones with `low`, `high`, `midpoint`, `width`, `strength` attributes
- [ ] **SVP-06**: LVN strength = `1 - (min_vol / V_mean)`; discard zones where strength < 0.30

### LVN Filtering (LVN)

- [ ] **LVN-01**: Filter A — POC proximity: discard any LVN midpoint within 3 ticks of current or prior session POCs
- [ ] **LVN-02**: Filter B — Multi-session confluence: keep only LVNs whose midpoint aligns (within ±2 ticks) with an LVN from at least one of the 2 prior sessions
- [ ] **LVN-03**: Filter C — Minimum separation: if two LVNs are within 4 ticks, keep only the one with higher strength
- [ ] **LVN-04**: Filter D — Real-time consolidation invalidation (run at each RTH bar close):
  - Sub-condition 1: ≥3 bars whose body (min/max of open,close) overlaps the LVN zone
  - Sub-condition 2: ≥4 midpoint crossings (consecutive bars on opposite sides)
  - Once invalidated: `valid=False`, never re-validate in same session
- [ ] **LVN-05**: Gap open invalidation: if the first RTH bar opens beyond the LVN (gap through it), immediately invalidate
- [ ] **LVN-06**: At session boundary (6 PM ET): clear ALL LVN zones; rebuild fresh for the new session

### TPO Bias (TPO)

- [ ] **TPO-01**: Build 30-minute bar TPO profile from pre-RTH bars only (18:00 → 09:29 ET)
- [ ] **TPO-02**: Compute session midpoint price; count TPO letters (30-min periods visiting each price level) in upper vs lower half
- [ ] **TPO-03**: Bias rules: `upper_ratio > 0.55` → BULLISH; `upper_ratio < 0.45` → BEARISH; otherwise → NEUTRAL
- [ ] **TPO-04**: If bias is NEUTRAL: skip the entire session (no trades taken)
- [ ] **TPO-05**: Bias is locked at 9:30 AM and does NOT update during RTH

### Single Prints (SP)

- [ ] **SP-01**: Build TPO profile (30-min periods visiting each price level) from session bars
- [ ] **SP-02**: A price level is a single print if: TPO count == 1 AND volume at that level < 0.15 × V_mean
- [ ] **SP-03**: Adjacent single print levels form SP zones; minimum zone height is 4 ticks; discard smaller zones
- [ ] **SP-04**: Overnight respect check: an SP zone is "respected" if price approached within 2 ticks, had a wick into the zone, but no bar body closed fully inside, during the overnight window (18:00–09:30 ET)
- [ ] **SP-05**: Only SP zones with `respected_overnight=True` are used as trade targets and bias confirmes

### Swing Detection (SWING)

- [ ] **SWING-01**: `detect_swing_highs(bars, lookback=5, min_swing_ticks=4)`: a swing high at bar `i` requires bar `i` to be the maximum in `bars[i-lookback:i+1]` AND each of bars `i+1` through `i+lookback` must have lower highs. Confirmed only when bar `i+lookback` closes.
- [ ] **SWING-02**: `detect_swing_lows(bars, lookback=5, min_swing_ticks=4)`: mirror of above for lows
- [ ] **SWING-03**: Minimum swing magnitude: `swing_price - neighbor_price >= min_swing_ticks × tick_size` (4 ticks = 1.0 NQ point)
- [ ] **SWING-04**: Every swing carries `bar_index` (where the extreme occurs) and `confirmed_at` (bar index when confirmed). Signal logic ONLY uses swings where `confirmed_at <= current_bar_index`.
- [ ] **SWING-05**: Reproducibility check: running swing detection twice on the same data produces byte-identical output

### ISMT Detection (ISMT)

- [ ] **ISMT-01**: Bearish ISMT: SH2 > SH1, confirmed within 10 bars, close back below SH1 within 3 bars of SH2 confirmation, sweep size < 2×ATR20
- [ ] **ISMT-02**: Bullish ISMT: SL2 < SL1, confirmed within 10 bars, close back above SL1 within 3 bars, sweep size < 2×ATR20
- [ ] **ISMT-03**: ISMT signals include: `confirmed_at`, `sweep_size`, signal direction, `entry_zone` reference price

### SMT Detection (SMT)

- [ ] **SMT-01**: Build synchronized NQ+ES bar stream (minute-floored timestamps, forward-fill missing, mark synthetic)
- [ ] **SMT-02**: Compute rolling 20-bar Pearson correlation between NQ and ES bar returns; only compute SMT when correlation ≥ 0.70
- [ ] **SMT-03**: Bearish SMT: NQ makes higher swing high (move ≥ 0.3×ATR20), ES does NOT (move ≤ +0.1×ATR20), within ±3 bars of each other, no synthetic bars involved
- [ ] **SMT-04**: Bullish SMT: NQ makes lower swing low (move ≤ -0.3×ATR20), ES does NOT (move ≥ -0.1×ATR20), within ±3 bars
- [ ] **SMT-05**: SMT signals include: `confirmed_at`, `divergence_strength`, `correlation_at_signal`

### Signal Priority (SIG)

- [ ] **SIG-01**: `get_structural_confirmation(direction)` checks for ISMT first, then SMT. Returns the strongest available signal within the last 5 bars.
- [ ] **SIG-02**: ISMT takes priority when both ISMT and SMT are present simultaneously
- [ ] **SIG-03**: In M2 feature engineering: `signal_source` feature (ISMT=1, SMT=0) captures the weighting distinction

### Entry Logic (ENTRY)

- [ ] **ENTRY-01**: 3-Step Model (Long): price approaches LVN from above, LVN still valid, bar closes above LVN zone (bullish close), bullish ISMT/SMT confirmed within last 5 bars, at least one respected SP zone above entry exists
- [ ] **ENTRY-02**: 3-Step Model (Short): mirror — price approaches LVN from below, LVN still valid, bar closes below LVN zone (bearish close), bearish ISMT/SMT within 5 bars, SP zone below exists
- [ ] **ENTRY-03**: Aggressive Ledge (Long): only in 9:25–10:00 AM window, price within 3 ticks of LVN, bias BULLISH, bar closes above LVN with bullish close; position size × 0.5
- [ ] **ENTRY-04**: Aggressive Ledge (Short): mirror for bearish bias and closes below LVN; position size × 0.5
- [ ] **ENTRY-05**: Pre-entry checklist enforced for all setups: RR ≥ 1.5, SL distance [4 ticks min, 1.5×ATR20 max], no bias NEUTRAL, direction matches bias, LVN valid, time before 3:45 PM ET, daily trades < 3

### Stop Loss (SL)

- [ ] **SL-01**: Long SL = `LVN_low - 0.5 × ATR_5`, snapped to tick grid
- [ ] **SL-02**: Short SL = `LVN_high + 0.5 × ATR_5`, snapped to tick grid
- [ ] **SL-03**: Hard floor: SL distance must be ≥ 4 ticks; if computed SL is tighter, reject the setup
- [ ] **SL-04**: Hard cap: SL distance must be ≤ 1.5 × ATR_20; if wider, reject the setup

### Take Profit & Exit Management (TP)

- [ ] **TP-01**: TP1 = bottom edge of nearest respected SP zone above entry (long) or top edge of nearest below (short)
- [ ] **TP-02**: TP2 = next SP zone in same direction; if no second SP zone within 3×ATR20, use next valid LVN in trade direction
- [ ] **TP-03**: At TP1 hit: exit `floor(full_size × 0.60)` contracts; move SL to entry price (breakeven)
- [ ] **TP-04**: At TP2 hit: exit all remaining contracts
- [ ] **TP-05**: Hard stop: if any bar's BODY (min/max of open,close) closes fully inside LVN zone → exit entire position at bar close
- [ ] **TP-06**: EOD close: force-flat all open positions at 3:45 PM ET bar close price
- [ ] **TP-07**: SL hit: exit entire remaining position at exact SL price (not bar close)

### Execution Engine (EXEC)

- [ ] **EXEC-01**: `TradeSetup` dataclass: setup_id, entry_price, stop_price, target_price (TP1), rr_ratio, direction, created_at, setup_type, lvn_ref, ismt_or_smt_ref
- [ ] **EXEC-02**: `TradeResult` dataclass: all TradeSetup fields + exit_price_tp1, exit_price_tp2 (or None), exit_type (FULL_TP / PARTIAL_TP / STOP / HARD_STOP / EOD / TIMEOUT), net_pnl, gross_pnl
- [ ] **EXEC-03**: Position sizing: `contracts = floor((100000 × 0.01) / (abs(entry - stop) × point_value))`; min 1 contract
- [ ] **EXEC-04**: Long gross PnL: `(exit - entry) × contracts × point_value`; Short: `(entry - exit) × contracts × point_value`
- [ ] **EXEC-05**: Commission: charged at entry AND each partial exit event separately; per-event cost = `contracts_in_event × commission_per_side`
- [ ] **EXEC-06**: Max 3 trades per session; after 3 entries, no new setups are evaluated for that session

### Reporting (REPORT)

- [ ] **REPORT-01**: Per-trade Plotly HTML chart: candlestick with entry/TP1/TP2/SL as horizontal lines, entry and all exit markers
- [ ] **REPORT-02**: Output to `D:\Algorithms\Wicked Backtest Results\run_YYYYMMDD_HHMMSS\charts\trade_NNN.html`
- [ ] **REPORT-03**: `trades.csv`: one row per completed trade with all TradeResult fields
- [ ] **REPORT-04**: `summary.md`: human-readable run summary with all institutional metrics
- [ ] **REPORT-05**: Results are saved incrementally (after each session/year) to prevent data loss on interruption

### Institutional Metrics (METRIC)

- [ ] **METRIC-01**: Daily P&L aggregation from trade results; daily returns = daily_pnl / account_size
- [ ] **METRIC-02**: Sharpe Ratio: `sqrt(252) × (mean(excess_returns) / std(excess_returns))`
- [ ] **METRIC-03**: Sortino Ratio: uses only downside std deviation in denominator
- [ ] **METRIC-04**: Max Drawdown: `min((equity - equity.expanding().max()) / equity.expanding().max())`
- [ ] **METRIC-05**: Profit Factor: `sum(positive_pnls) / abs(sum(negative_pnls))`
- [ ] **METRIC-06**: Win rate, average win, average loss, total trades, total P&L

### Audit & Reproducibility (AUDIT)

- [ ] **AUDIT-01**: Reproducibility gate: full backtest run twice on same date range produces byte-identical `trades.csv`
- [ ] **AUDIT-02**: RR divide-by-zero guard: `if entry == stop: skip_setup`
- [ ] **AUDIT-03**: Short P&L polarity validated by unit test with known trade outcome
- [ ] **AUDIT-04**: Drawdown uses rolling peak (`expanding().max()`), not fixed baseline
- [ ] **AUDIT-05**: HTF resample uses `label='left', closed='left'` to prevent label lookahead
- [ ] **AUDIT-06**: Commission: entry charges + one-or-two exit charges (depending on how many partial exits occurred)
- [ ] **AUDIT-07**: Exit prices use exact stop/target prices, not the triggering bar's close

---

## V2 Requirements (Milestone 2 — ML + Monte Carlo)

*Deferred to M2. Not in scope for V1 but documented for forward planning.*

- [ ] Feature engineering (12+ features, all lookback-safe) — Phase 8
- [ ] Walk-forward analysis (730-day train / 180-day OOS) — Phase 9
- [ ] XGBoost + Optuna walk-forward training — Phase 10
- [ ] Dual-instrument synchronized Monte Carlo chunk splicing — Phase 11
- [ ] Per-candle lognormal scalar (mu=0, sigma=0.3, shared NQ+ES) — Phase 11
- [ ] Full signal re-detection on synthetic paths (reality-first) — Phase 11
- [ ] Dashboard: equity cone + PnL histogram + metric panel — Phase 12
- [ ] CSV outputs: feature_dataset.csv, inference_log.csv, monte_carlo_raw_paths.csv, summary.json — Phases 10-12

---

## Out of Scope

| Item | Reason |
|------|--------|
| Live/paper trading execution | M1 is backtesting only |
| Tick data (bid/ask spreads) | OHLCV approximation used; acceptable for institutional metrics |
| Multi-strategy portfolio | Single strategy only |
| News event calendar | Edge case; reduces complexity |
| Deep learning (LSTM, transformer) | XGBoost + RF sufficient for M2 |
| ES as primary trading instrument | NQ is primary; ES is SMT/ISMT confluence only |

---

## Traceability

*Populated by roadmapper agent.*

| Requirement | Phase |
|-------------|-------|
| DATA-01 through DATA-07, CORE-01 through CORE-03 | Phase 1 |
| SWING-01 through SWING-05, TPO-01 through TPO-05 | Phase 2 |
| SVP-01 through SVP-06, LVN-01 through LVN-06, SP-01 through SP-05 | Phase 3 |
| ISMT-01 through ISMT-03, SMT-01 through SMT-05, SIG-01 through SIG-03, ENTRY-01 through ENTRY-05 | Phase 4 |
| SL-01 through SL-04, TP-01 through TP-07, EXEC-01 through EXEC-06, REPORT-01 through REPORT-05 | Phase 5 |
| METRIC-01 through METRIC-06 | Phase 6 |
| AUDIT-01 through AUDIT-07 | Phase 7 |
