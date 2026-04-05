# Phase 4: Signal Generation (ISMT + SMT + Entry) - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement ISMT detection (single-instrument NQ), SMT detection (dual-instrument NQ+ES with Pearson correlation filter), combine into `get_structural_confirmation()`, and implement both entry models (3-Step Model and Aggressive Ledge). This phase produces `TradeSetup` objects consumed by Phase 5's execution engine.

</domain>

<decisions>
## Implementation Decisions

### ISMT Confirmation Window
- **D-01:** The 3-bar "close back through" window starts from `SH2.confirmed_at` (NOT `SH2.bar_index`). Starting from `bar_index` is lookahead — it checks for a close below SH1 before the algorithm legally knows SH2 exists.
- **D-02:** Window opens on the bar immediately AFTER `SH2.confirmed_at` and closes 3 bars later. This means ISMT signals fire later than a human eyeballing the pattern — that's correct and intentional.
- **D-03:** Some ISMT signals will be "stale" by confirmation time (price already moved). These will fail the recency check in `get_structural_confirmation()` and get discarded. Better to miss a signal than act on one requiring future knowledge.

### Signal Priority — Equal Weight, Recency Tiebreak
- **D-04:** **ISMT and SMT have equal priority.** Neither type inherently beats the other. When both are present in the 5-bar window, return the **most recent one** by `confirmed_at`. Recency is the only tiebreak — the freshest structural confirmation is the most actionable.
- **D-05:** The 5-bar recency window is always measured backwards from the bar currently being evaluated for entry, inclusive. Evaluating bar 247 → valid signals are those confirmed at bars 243–247.
- **D-06:** If a signal's source swings have been invalidated (price traded back through them), discard that signal entirely and use the next most recent valid signal of either type.
- **D-07:** In M2 feature engineering, `signal_source` feature encodes ISMT=1, SMT=0 — no weighting difference at signal selection time, but the ML model may learn differential predictive power.

### "Approaches LVN" Definition
- **D-08:** Two conditions must BOTH be true simultaneously for a long approach (bullish, approaching from above):
  1. **Touch condition:** Current bar's low ≤ `LVN_high + 3 ticks` (price is within range of the zone)
  2. **Directional approach:** All of the prior 3 bars' closes are strictly above `LVN_high` (confirms price came from above, not chopping around the zone)
- **D-09:** For short approach (bearish, approaching from below): mirror — current bar's high ≥ `LVN_low - 3 ticks` AND prior 3 bars' closes strictly below `LVN_low`.
- **D-10:** The current bar does NOT need to close above/below the LVN at approach detection time — the close requirement is the entry trigger that comes after, not the approach detector.
- **D-11:** This two-part definition is a second line of defense against firing during consolidation (in addition to LVN-04 consolidation invalidation from Phase 3).

### Aggressive Ledge Window Behavior
- **D-12:** Every bar in the 9:25–10:00 AM window that meets conditions is a valid setup candidate. Do NOT special-case the first qualifying bar — if price produces a cleaner rejection at 9:44 than at 9:31, the 9:44 bar should be taken.
- **D-13:** Daily trade counter (max 3) applies globally across BOTH setup types (3-Step Model and Aggressive Ledge). Not separate limits per type.
- **D-14:** Once a setup at a specific LVN fires and results in a trade (win or loss), suppress that same LVN as an aggressive ledge source for the remainder of the session. Prevents re-entering the same LVN repeatedly when it keeps getting touched — after the first trade at that level, the edge is reduced.

### Agent's Discretion
- SMT correlation computation: use `numpy.corrcoef` on 20-bar return arrays for rolling Pearson. More efficient than pandas `.corr()` in a bar-by-bar loop.
- ISMT and SMT dataclasses carry `invalidated` flag that gets set if source swings are traded through post-signal.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Strategy Specification
- `.planning/REQUIREMENTS.md` — ISMT-01 through ISMT-03, SMT-01 through SMT-05, SIG-01 through SIG-03, ENTRY-01 through ENTRY-05
  - **NOTE:** SIG-02 ("ISMT takes priority") is SUPERSEDED by D-04 above — equal priority with recency tiebreak.
- `.planning/PROJECT.md` — Strategy summary, signal priority section
  - **NOTE:** "Signal priority: ISMT > SMT" is SUPERSEDED — equal priority, most recent wins.

### Architecture & Design
- `.planning/research/ARCHITECTURE.md` — RTH execution phase data flow, dual-instrument synchronization
- `.planning/research/PITFALLS.md` — P3 (entry on intra-bar signal — all eval happens after bar close), P7 (SMT false signal on synthetic bars), P2 (symmetric swing lookahead — consumed via Phase 2's confirmed swings)

### Prior Phase Context
- `.planning/phases/01-data-infrastructure-core-candle-math/01-CONTEXT.md` — D-04/D-06 (synthetic bar handling: forward-fill all OHLCV, skip SMT windows with >2/20 synthetic), D-10 (`ismt.py`, `smt.py`, `entry.py` module ownership)
- `.planning/phases/02-swing-detection-tpo-bias-engine/02-CONTEXT.md` — D-01–D-03 (swing registry with prior session tail buffer, query by merging lists)
- `.planning/phases/03-volume-profile-lvn-single-prints/03-CONTEXT.md` — D-03 (VolumeProfile object, LVN validity tracking), D-10–D-12 (SP zone respected_overnight flag)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Phase 2 provides: `swings.py` (confirmed swings with `bar_index` and `confirmed_at`), swing registry with `current_session_swings` + `prior_session_tail`
- Phase 3 provides: `lvn.py` (filtered LVN zones with validity tracking), `single_prints.py` (SP zones with `respected_overnight` flag)
- Phase 1 provides: `data_loader.py` (synchronized NQ+ES stream with `is_synthetic` tag), `core.py` (ATR_5, ATR_20)

### Established Patterns
- All signal evaluation happens AFTER bar close — no intra-bar signals (P3 pitfall)
- Synthetic bars suppress SMT computation (Phase 1 D-06)
- Session-scoped state with prior-session carryover where needed (swing tail buffer pattern from Phase 2)

### Integration Points
- `ismt.py` consumes: swings from `swings.py`, ATR from `core.py`
- `smt.py` consumes: swings from both NQ and ES swing registries, synchronized bar stream, correlation from `core.py`/`numpy`
- `entry.py` consumes: LVN zones from `lvn.py`, structural confirmation from `ismt.py`/`smt.py`, SP zones from `single_prints.py`, TPO bias from `tpo.py`
- `entry.py` produces: `TradeSetup` objects consumed by `position.py` (Phase 5)

</code_context>

<specifics>
## Specific Ideas

- User specified exact approach formula: current bar low ≤ `LVN_high + 3 ticks` AND prior 3 closes strictly above `LVN_high`
- User specified per-LVN suppression after aggressive ledge trade: once an LVN produces a trade, it's suppressed for aggressive ledge entries for the rest of the session
- User revised signal priority to equal (neither ISMT nor SMT inherently wins) — recency tiebreak when both present
- User specified the exception path: invalidated source swings → discard that signal → use next most recent valid signal of either type

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-signal-generation-ismt-smt-entry*
*Context gathered: 2026-04-05*
