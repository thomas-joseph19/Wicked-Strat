# ROADMAP — Wicked LVN/Ledge Strategy Backtest Engine

## Milestone 1: Mechanical Backtest Engine
**Goal**: Produce a hindsight-free, reproducible trade log with institutional metrics across 12 years of NQ/ES data (2014-01-02 → 2026-01-30). This is the ground truth that all downstream ML work depends on.

---

### Phase 1: Data Infrastructure & Core Candle Math
**Status**: 🔲 Not started
**Goal**: Load both parquet datasets, normalize to a unified schema, implement session boundary logic, build a synchronized dual-instrument bar stream, and provide foundational math (ATR).
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, DATA-06, DATA-07, CORE-01, CORE-02, CORE-03

**Success Criteria**:
1. `python main.py --mode backtest --start 2014-01-02 --end 2014-12-31` loads and iterates all bars without error; total bar count matches expected row count from parquet inspection
2. Session ID assignment is verified: a bar at 18:30 ET is assigned to the next day's session; a bar at 17:30 ET is assigned to the current day's session
3. DST correctness: bars on the first Monday after a spring-forward transition show 9:30 AM ET session open correctly (not 10:30 AM or 8:30 AM)
4. ATR_5 and ATR_20 computed at bar index `i` use only `bars[0:i+1]` data; verified by inspection of first 25 bars (ATR_5 is None for bars 0–3, first valid value at bar 4)
5. Synchronized NQ+ES stream: for a randomly sampled 1-hour window, every minute has both NQ and ES bars; missing bars are synthetic with `is_synthetic=True`

---

### Phase 2: Swing Detection & TPO Bias Engine
**Status**: 🔲 Not started
**Goal**: Implement hindsight-free swing high/low detection with mandatory confirmation delay, and compute pre-market TPO bias from 30-minute bars locked at 9:30 AM ET.
**Requirements**: SWING-01, SWING-02, SWING-03, SWING-04, SWING-05, TPO-01, TPO-02, TPO-03, TPO-04, TPO-05

**Success Criteria**:
1. A swing high at bar index `i` with `lookback=5` has `confirmed_at = i+5`; when the backtest loop is at bar `b`, only swings with `confirmed_at <= b` are visible — verified on a known 10-day sample by comparing detected swings to a manual chart review
2. Running swing detection twice on the same 30-day slice produces byte-identical output (no state mutation)
3. TPO bias for a known bullish session (where price clearly closed above session midpoint all day) returns BULLISH; for a flat session, returns NEUTRAL and 0 trades are generated
4. 30-minute bars are correctly aggregated using `label='left', closed='left'` — verified that a session's first 30-min bar covers 18:00–18:30 ET, not 18:30–19:00
5. Swing threshold: a 3-tick swing (below min_swing_ticks=4) is NOT flagged as a swing; a 5-tick swing IS flagged

---

### Phase 3: Volume Profile + LVN + Single Prints
**Status**: 🔲 Not started
**Goal**: Build Session Volume Profiles from pre-RTH bars, detect and filter LVN zones through all 4 filters, detect single print zones, and verify overnight respect for target selection.
**Requirements**: SVP-01, SVP-02, SVP-03, SVP-04, SVP-05, SVP-06, LVN-01, LVN-02, LVN-03, LVN-04, LVN-05, LVN-06, SP-01, SP-02, SP-03, SP-04, SP-05

**Success Criteria**:
1. SVP is built only from bars with `timestamp < 09:30 ET`; adding post-RTH bars produces a different (larger) profile — verified by comparing bar counts in each profile
2. LVN multi-session confluence: an LVN present only in current session (no match in 2 prior sessions) is discarded; an LVN present across all 3 sessions passes — verified on a manually inspected date
3. LVN consolidation invalidation: after 3 bars with body overlap, the LVN is marked `valid=False` and never re-used in that session; a subsequent bar touching the same price level generates no signal
4. Gap open invalidation: if the 9:30 AM opening bar gaps through an LVN zone (opens on the other side), that LVN is immediately set `valid=False` before any entry checking occurs
5. Single print zone overnight respect: an SP zone where the overnight wicked into it but no body closed inside returns `respected_overnight=True`; an SP zone where a body closed fully inside returns `False`

---

### Phase 4: Signal Generation (ISMT + SMT + Entry)
**Status**: 🔲 Not started
**Goal**: Implement ISMT detection (single-instrument), SMT detection (dual-instrument with Pearson correlation filter), combine into `get_structural_confirmation()`, and implement both entry models (3-Step and Aggressive Ledge).
**Requirements**: ISMT-01, ISMT-02, ISMT-03, SMT-01, SMT-02, SMT-03, SMT-04, SMT-05, SIG-01, SIG-02, SIG-03, ENTRY-01, ENTRY-02, ENTRY-03, ENTRY-04, ENTRY-05

**Plans:** 5 plans (4 waves: 0–3)

Plans:
- [ ] `04-00-PLAN.md` — Wave 0: `tests/phase04/` + `pyproject.toml` pytest + `TradeSetup` in `position.py` (shared harness)
- [ ] `04-01-PLAN.md` — Wave 1: `ismt.py` + `test_ismt.py` (ISMT-01..03, D-01–D-03)
- [ ] `04-02-PLAN.md` — Wave 1: `smt.py` + `test_smt.py` (SMT-01..05, D-06, P7)
- [ ] `04-03-PLAN.md` — Wave 2: `get_structural_confirmation` + `test_structural_confirmation.py` (SIG-01..03 per D-04–D-06; REQ SIG-02 superseded)
- [ ] `04-04-PLAN.md` — Wave 3: 3-Step + Aggressive Ledge + ENTRY-05 + entry tests

**Success Criteria**:
1. ISMT bearish: given a known pattern (SH2 > SH1, close back below SH1 within 3 bars), the signal fires at the correct bar; given a genuine breakout (move > 2×ATR20), no ISMT is generated
2. SMT: when rolling correlation (20-bar window) is 0.65, SMT signals are suppressed; when correlation is 0.85, SMT signals are permitted — verified with a constructed test dataset
3. SMT signals are never generated when either NQ or ES bar is synthetic (`is_synthetic=True`)
4. *(Superseded by `04-CONTEXT.md` D-04–D-06 for implementation/tests.)* ~~ISMT takes priority over SMT when both are present simultaneously — `get_structural_confirmation()` returns ISMT source first~~ **Replace with:** equal priority; **recency** (`confirmed_at`) tiebreaks; invalidated signals skipped.
5. Aggressive Ledge: a setup at 09:28 AM is rejected (outside window); at 09:32 AM in the 9:25-10:00 window is accepted; at 10:05 AM is rejected
6. 3-Step Model: verified that all three conditions (active LVN, structural confirmation within 5 bars, respected SP zone in trade direction) must be true simultaneously — removing any one condition suppresses the signal

---

### Phase 5: Trade Execution Engine & Reporting
**Status**: 🔲 Not started
**Goal**: Resolve every TradeSetup against subsequent bars, implement full 60%/40% partial exit logic, compute P&L (long and short), generate per-trade Plotly HTML charts, and write output to D:\Algorithms\Wicked Backtest Results.
**Requirements**: SL-01, SL-02, SL-03, SL-04, TP-01, TP-02, TP-03, TP-04, TP-05, TP-06, TP-07, EXEC-01, EXEC-02, EXEC-03, EXEC-04, EXEC-05, EXEC-06, REPORT-01, REPORT-02, REPORT-03, REPORT-04, REPORT-05

**Success Criteria**:
1. Short trade P&L polarity: a short trade entered at 18,000, stopped at 18,050 produces a NEGATIVE net P&L; a short trade exited at 17,950 produces a POSITIVE net P&L
2. Partial exit accounting: a 5-contract position at TP1 exits 3 contracts (floor of 60%); remaining 2 contracts continue; at TP2 both exit; total commission = (5 × commission) entry + (3 × commission) TP1 exit + (2 × commission) TP2 exit
3. Hard stop: a bar whose BODY (min(open,close) to max(open,close)) spans the LVN zone triggers immediate full exit at that bar's close; a bar whose WICK enters the zone but body stays clean does NOT trigger hard stop
4. Max daily trades: after 3 entries in one session, no further entries are evaluated for that day — verified on a volatile test session that would otherwise generate 5+ signals
5. Per-trade HTML chart exists in output directory for every completed trade; opening a chart in a browser shows candlestick with entry/SL/TP1/TP2 lines and entry+exit markers
6. `trades.csv` contains correct fields including partial exit prices and individual fill commissions

---

### Phase 6: Institutional Metrics
**Status**: 🔲 Not started
**Goal**: Aggregate trade results to daily P&L, compute all risk-adjusted performance metrics, and produce the final summary.md.
**Requirements**: METRIC-01, METRIC-02, METRIC-03, METRIC-04, METRIC-05, METRIC-06

**Success Criteria**:
1. Daily P&L aggregation: on a day with two trades (+$800 and -$200), daily P&L = +$600; daily return = $600 / $100,000 = 0.006
2. Max Drawdown uses rolling peak (`equity.expanding().max()`), NOT fixed starting equity — verified by constructing an equity curve that dips, recovers, then dips deeper: the second dip must show the larger drawdown
3. Profit Factor = infinity guard: on a test set with zero losing trades, returns `gross_wins` (not `inf` or error)
4. Sharpe and Sortino annualized using `sqrt(252)` multiplier on daily returns
5. `summary.md` contains all 6 metric categories and is human-readable; opens correctly in any markdown viewer

---

### Phase 7: Trade Logic Audit & Verification
**Status**: 🔲 Not started
**Goal**: Run the full audit checklist from the specification, pass the reproducibility gate (2 identical runs = identical trades.csv), and fix any remaining bugs before designating M1 complete.
**Requirements**: AUDIT-01, AUDIT-02, AUDIT-03, AUDIT-04, AUDIT-05, AUDIT-06, AUDIT-07

**Success Criteria**:
1. **Reproducibility gate**: running the full backtest twice (same date range, same config) produces byte-identical `trades.csv` — zero differences
2. **RR guard**: a constructed setup where entry == stop_price generates no trade (skipped, not a crash)
3. **Short polarity test**: a synthetic short trade with known entry/exit produces exactly the expected net P&L (positive when price fell, negative when price rose) — unit tested
4. **Drawdown check**: max drawdown on the full equity curve is negative (not positive) and uses rolling peak
5. **Commission validation**: a full trade (entry → TP1 partial → TP2 full) charges exactly 3 commission events (not 4); a stopped-out trade charges exactly 2 events (entry + stop exit)
6. **Resample check**: 30-minute bar aggregation labels are verified with `label='left', closed='left'` on a known session
7. **Audit report**: a written audit_report.md documents the results of each checklist item with pass/fail

---

## Milestone 2: ML Optimization & Monte Carlo
**Goal**: Apply walk-forward ML filtering to identify high-probability setups and stress-test via dual-instrument reality-first Monte Carlo simulation.
**Status**: 🔒 Deferred — begins after M1 complete and audit passes

**Phases (outline):**
- **Phase 8** — Feature Engineering: Convert TradeResult objects into ML feature vectors (12+ lookback-safe features, label assignment)
- **Phase 9** — Walk-Forward Data Partitioning: 730-day train / 180-day OOS windows, no shuffling
- **Phase 10** — Model Training & Signal Filtering: XGBoost + Optuna, dynamic threshold selection, class imbalance handling
- **Phase 10.5** — Pilot Smoke Test: 2-year run (50 paths, 5 Optuna trials) before overnight full run
- **Phase 11** — Dual-Instrument Monte Carlo: synchronized chunk splicing, lognormal per-candle scalar (shared NQ+ES), slippage stress, ruin barrier
- **Phase 12** — Dashboard & Final Metrics: Plotly equity cone + PnL histogram, all metrics (EV, Ruin Rate, p-value, Calmar), CSV outputs
