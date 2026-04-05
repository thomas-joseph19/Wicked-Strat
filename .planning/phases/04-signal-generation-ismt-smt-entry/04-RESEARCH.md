# Phase 04: Signal Generation (ISMT + SMT + Entry) — Research

**Researched:** 2026-04-05  
**Domain:** Stateful bar-close signal generation (single- and dual-instrument), structural confirmation selection, LVN/SP-gated entries  
**Overall confidence:** HIGH for semantics (locked in CONTEXT); MEDIUM for implementation edge cases until code + tests exist

<user_constraints>
## User Constraints (from 04-CONTEXT.md)

### Locked Decisions

#### ISMT Confirmation Window
- **D-01:** The 3-bar "close back through" window starts from `SH2.confirmed_at` (NOT `SH2.bar_index`). Starting from `bar_index` is lookahead — it checks for a close below SH1 before the algorithm legally knows SH2 exists.
- **D-02:** Window opens on the bar immediately AFTER `SH2.confirmed_at` and closes 3 bars later. This means ISMT signals fire later than a human eyeballing the pattern — that's correct and intentional.
- **D-03:** Some ISMT signals will be "stale" by confirmation time (price already moved). These will fail the recency check in `get_structural_confirmation()` and get discarded. Better to miss a signal than act on one requiring future knowledge.

#### Signal Priority — Equal Weight, Recency Tiebreak
- **D-04:** **ISMT and SMT have equal priority.** Neither type inherently beats the other. When both are present in the 5-bar window, return the **most recent one** by `confirmed_at`. Recency is the only tiebreak — the freshest structural confirmation is the most actionable.
- **D-05:** The 5-bar recency window is always measured backwards from the bar currently being evaluated for entry, inclusive. Evaluating bar 247 → valid signals are those confirmed at bars 243–247.
- **D-06:** If a signal's source swings have been invalidated (price traded back through them), discard that signal entirely and use the next most recent valid signal of either type.
- **D-07:** In M2 feature engineering, `signal_source` feature encodes ISMT=1, SMT=0 — no weighting difference at signal selection time, but the ML model may learn differential predictive power.

#### "Approaches LVN" Definition
- **D-08:** Two conditions must BOTH be true simultaneously for a long approach (bullish, approaching from above):
  1. **Touch condition:** Current bar's low ≤ `LVN_high + 3 ticks` (price is within range of the zone)
  2. **Directional approach:** All of the prior 3 bars' closes are strictly above `LVN_high` (confirms price came from above, not chopping around the zone)
- **D-09:** For short approach (bearish, approaching from below): mirror — current bar's high ≥ `LVN_low - 3 ticks` AND prior 3 bars' closes strictly below `LVN_low`.
- **D-10:** The current bar does NOT need to close above/below the LVN at approach detection time — the close requirement is the entry trigger that comes after, not the approach detector.
- **D-11:** This two-part definition is a second line of defense against firing during consolidation (in addition to LVN-04 consolidation invalidation from Phase 3).

#### Aggressive Ledge Window Behavior
- **D-12:** Every bar in the 9:25–10:00 AM window that meets conditions is a valid setup candidate. Do NOT special-case the first qualifying bar — if price produces a cleaner rejection at 9:44 than at 9:31, the 9:44 bar should be taken.
- **D-13:** Daily trade counter (max 3) applies globally across BOTH setup types (3-Step Model and Aggressive Ledge). Not separate limits per type.
- **D-14:** Once a setup at a specific LVN fires and results in a trade (win or loss), suppress that same LVN as an aggressive ledge source for the remainder of the session. Prevents re-entering the same LVN repeatedly when it keeps getting touched — after the first trade at that level, the edge is reduced.

### Claude's Discretion
- SMT correlation computation: use `numpy.corrcoef` on 20-bar return arrays for rolling Pearson. More efficient than pandas `.corr()` in a bar-by-bar loop.
- ISMT and SMT dataclasses carry `invalidated` flag that gets set if source swings are traded through post-signal.

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description (from REQUIREMENTS.md) | Research support |
|----|--------------------------------------|------------------|
| ISMT-01 | Bearish ISMT: SH2 > SH1, confirmed within 10 bars, close back below SH1 within 3 bars of SH2 confirmation, sweep < 2×ATR20 | Pair swing selection from merged registry; 3-bar window anchored to `SH2.confirmed_at` (D-01–D-02); sweep vs ATR20 at signal bar |
| ISMT-02 | Bullish ISMT: mirror with swing lows | Same as ISMT-01 for lows |
| ISMT-03 | Signals carry `confirmed_at`, `sweep_size`, direction, `entry_zone` ref | Emit dataclass at ISMT completion bar; `confirmed_at` = bar where pattern fully satisfied |
| SMT-01 | Synchronized NQ+ES stream | `data_loader.py` pairs; minute alignment + `is_synthetic` |
| SMT-02 | Rolling 20-bar Pearson on returns; SMT only if correlation ≥ 0.70 | `numpy.corrcoef` on `r_nq[i-19:i+1]`, `r_es[i-19:i+1]`; skip window if >2/20 synthetic (Phase 1 D-06) |
| SMT-03 | Bearish SMT: NQ higher SH vs ES not, moves vs ATR20, ±3 bars, no synthetic | Compare **confirmed** swings; magnitude gates; bar-alignment |
| SMT-04 | Bullish SMT: mirror for lows | Same |
| SMT-05 | Signal fields: `confirmed_at`, `divergence_strength`, `correlation_at_signal` | Populate at SMT detection bar |
| SIG-01 | Structural confirmation within last 5 bars | **Implement per D-04–D-06:** equal priority, recency tiebreak, invalidation — REQ text "ISMT first" is **superseded** |
| SIG-02 | REQ: ISMT priority when both present | **SUPERSEDED by D-04** — do not implement ISMT-first |
| SIG-03 | M2 `signal_source` encoding ISMT=1, SMT=0 | Preserve on `TradeSetup` / feature row for later phases |
| ENTRY-01 | 3-Step long: approach from above, valid LVN, close above zone + bullish close, bullish structural conf in 5 bars, respected SP above | Compose `approaches_lvn_long`, LVN validity, close rules, `get_structural_confirmation(BULLISH)`, SP query |
| ENTRY-02 | 3-Step short: mirror | Same with bearish semantics |
| ENTRY-03 | Aggressive ledge long: 9:25–10:00, within 3 ticks of LVN, bias BULLISH, close above LVN + bullish close; size ×0.5 | `session.py` window; separate proximity rule (3 ticks) vs approach definition |
| ENTRY-04 | Aggressive ledge short: mirror | Same |
| ENTRY-05 | Pre-entry checklist: RR ≥ 1.5, SL distance [4 ticks, 1.5×ATR20], bias not NEUTRAL, direction matches bias, LVN valid, time < 3:45 PM, daily trades < 3 | Central `validate_trade_setup()` used by both entry paths; needs ATR from `core.py` |

**Traceability note:** `.planning/REQUIREMENTS.md` still states SIG-01/SIG-02 as ISMT-first. **Phase 4 implementation and tests MUST follow `04-CONTEXT.md` D-04–D-06.** Update REQUIREMENTS in a docs pass if desired; planner must not treat ROADMAP/REQ as overriding CONTEXT.
</phase_requirements>

## Executive Summary

Phase 4 sits at the seam between **hindsight-free market structure** (Phases 1–3) and **execution** (Phase 5). It must consume only information knowable at the **close** of the current bar: confirmed swings (`confirmed_at ≤ current_bar_index`), frozen TPO bias, LVN validity flags, respected SP zones, synchronized NQ/ES bars with synthetic tagging, and ATR series that exclude synthetic bars (Phase 1).

Implement three cooperating modules under `src/` as fixed in Phase 1: `ismt.py` (NQ-only patterns), `smt.py` (NQ vs ES divergence under correlation and synthetic gating), and `entry.py` (3-Step Model, Aggressive Ledge, `get_structural_confirmation()`, and `TradeSetup` construction). The highest-risk bugs are **lookahead** (using `bar_index` instead of `confirmed_at` for ISMT windows — D-01), **false SMT on synthetic ES** (P7), and **intra-bar evaluation** (P3). Tests should be built from **minimal synthetic bar streams** where expected signals are countable by hand.

**Primary recommendation:** Implement ISMT and SMT as **pure detectors** that append to session-scoped deques of signal objects; implement `get_structural_confirmation(direction, current_bar_index, ...)` as a **selector** that filters by direction, 5-bar recency (D-05), invalidation (D-06), and then picks **max(`confirmed_at`)** across surviving ISMT and SMT candidates (D-04). Keep ENTRY-05 checks in one function used by both entry models.

---

## Standard Stack

### Core

| Library | Version (verified / policy) | Purpose | Why standard |
|---------|----------------------------|---------|--------------|
| Python | 3.9+ (project: 3.14 observed) | Runtime | `zoneinfo`, dataclasses |
| numpy | 2.2.6 installed; PyPI latest 2.4.4 (2026-04-05) | `corrcoef`, arrays | Phase 1 discretion + vectorized small windows |
| pandas | 2.x per STACK.md | Session grouping, optional helpers | Bar tables, groupby |

### Supporting

| Library | Purpose | When |
|---------|---------|------|
| pytest | Unit tests | Nyquist-style verification; install if missing (`python -m pytest`) |

**Correlation implementation (locked + standard):** At bar index `i`, let `r_nq[k] = (close_nq[k]-close_nq[k-1])/close_nq[k-1]` (or log-return; pick one and document). Take slices `r_nq[i-19:i+1]` and `r_es[i-19:i+1]` (length 20). If Phase 1 synthetic rule fires for that window, **do not compute SMT**. Else `corr = numpy.corrcoef(r_nq, r_es)[0,1]`. Guard `nan` (zero variance) as "no SMT."

**Installation (dev):** `pip install numpy pandas pyarrow pytest` (align with `requirements.txt` when Phase 1 adds it).

---

## Technical Approach by Subsystem

### ISMT (NQ only)

**Inputs:** Merged swing list from `swings.py` (`current_session_swings` + `prior_session_tail`), sorted by `confirmed_at`; NQ `ATR_20` at relevant indices from `core.py`; `current_bar_index` (evaluation happens **after** this bar closes).

**Suggested API shapes:**

- `IsmtSignal` dataclass: `direction`, `confirmed_at: int`, `sweep_size: float`, `entry_zone: float` (e.g. SH1/SL1 price per spec), `source_swings: tuple[Swing, ...]`, `invalidated: bool = False`, `signal_kind: Literal["ISMT"] = "ISMT"`.
- `detect_ismt_for_bar(nq_bars, swings_up_to_now, atr20_by_bar, current_bar_index, thresholds) -> Optional[IsmtSignal]` **or** incremental `IsmtTracker.update(bar) -> Optional[IsmtSignal]`.

**Bearish (ISMT-01) — operational definition for planning:**

1. Identify two **confirmed** swing highs `SH1`, `SH2` with `SH2.price > SH1.price` (min swing magnitude already enforced by SWING-03).
2. **Timing:** `SH2.confirmed_at - SH1.confirmed_at <= 10` bars (interpretation: both swings exist in-order within 10 bars of each other's confirmation chain — planner should fix exact inequality to match PROJECT.md if it differs).
3. **Close-back window (D-01, D-02):** Let `t = SH2.confirmed_at`. Examine **only** bars at indices `t+1`, `t+2`, `t+3`. Require ∃ bar in that set whose **close** `< SH1.price` (bearish ISMT).
4. **Sweep size:** `sweep_size = SH2.price - SH1.price` (or vs relevant reference); require `sweep_size < 2 * ATR20[bar]` where `bar` is the ISMT **signal completion** index (planner: align to bar where condition last becomes true — typically the close-back bar, document in PLAN).
5. **Emit signal** with `confirmed_at` = index where the pattern is **fully** satisfied (last required close-back bar), not `SH2.bar_index`.

**Bullish (ISMT-02):** Mirror with swing lows, close back **above** `SL1` in the same `t+1..t+3` window.

**Invalidation (D-06, discretion):** If subsequent NQ price trades **through** levels that define the pattern (e.g. close back above `SH1` for a bearish ISMT), set `invalidated=True` so `get_structural_confirmation` skips it.

---

### SMT (correlation + synthetic bar gating)

**Inputs:** Synchronized stream from `data_loader.py` (`nq_bar`, `es_bar` per minute) with `is_synthetic` on each; separate ES swing registry (same `swings.py` logic on ES series); NQ `ATR_20`; numpy correlation.

**Gating layers:**

1. **P7 / SMT-03:** If either NQ or ES bar at the comparison index is synthetic, **no SMT** for that candidate (REQ: "no synthetic bars involved").
2. **Phase 1 D-06:** For the 20-bar correlation window ending at `i`, if **more than 2** bars are synthetic, **skip** correlation and SMT for that bar.
3. **SMT-02:** Only evaluate divergence if `correlation ≥ 0.70`.

**Rolling correlation:** Use `numpy.corrcoef` on 20 consecutive **returns** (discretion). Align ES and NQ on the **same minute index** after sync.

**Bearish SMT (SMT-03) — structure:**

- NQ registers a **higher** swing high with move ≥ `0.3 * ATR20` (relative to reference swing — planner ties to prior swing high).
- ES **does not** make a matching higher high: move ≤ `+0.1 * ATR20`.
- **Time alignment:** NQ swing confirmation and ES swing confirmation within **±3 bars** (compare `confirmed_at` values).
- Emit `SmtSignal` with `correlation_at_signal`, `divergence_strength` (define as e.g. NQ_move - ES_move or normalized delta — planner picks one formula and freezes).

**Bullish SMT (SMT-04):** Mirror with lows and negative thresholds.

**`confirmed_at` for SMT:** Bar index where the divergence rule is **fully** satisfied under bar-close semantics (often the later of the two swing confirmations once the pair is valid).

---

### `get_structural_confirmation()`

**Signature (suggested):**

```python
def get_structural_confirmation(
    direction: Literal["BULLISH", "BEARISH"],
    current_bar_index: int,
    ismt_signals: Sequence[IsmtSignal],
    smt_signals: Sequence[SmtSignal],
) -> IsmtSignal | SmtSignal | None:
    ...
```

**Algorithm (D-04–D-06):**

1. Filter candidates matching `direction` and `not invalidated`.
2. Keep those with `confirmed_at` in `[current_bar_index - 4, current_bar_index]` **inclusive** (5-bar window — D-05).
3. Sort by `confirmed_at` descending; return first still-valid after **invalidation** rules (or scan: prefer strict recency).

**Important:** Do **not** prefer ISMT over SMT. If two candidates share the same `confirmed_at` (degenerate test case), define deterministic tie-break (e.g. stable sort by kind for reproducibility — document in tests).

**SIG-03:** Attach which concrete object won so M2 can set `signal_source` (ISMT=1, SMT=0) on the setup.

---

### 3-Step Model entry

**Long (ENTRY-01) — checklist composition:**

1. **Approach (D-08):** `approaches_lvn_from_above(lvn, bars, i)` using **touch** + **prior 3 closes strictly above `LVN_high`**.
2. **LVN valid:** `lvn.valid` from `lvn.py` (LVN-04/05 already applied upstream).
3. **Trigger:** Bar `i` **closes above** `LVN.high` and close is **bullish** (close > open per strategy definition — confirm in PROJECT.md).
4. **Structure:** `get_structural_confirmation("BULLISH", i, ...)` non-None.
5. **Target existence:** At least one **respected** SP zone above entry from `single_prints.py` (`respected_overnight=True`).

**Short (ENTRY-02):** Mirror with D-09, bearish close, bearish structure, SP below.

**Bar index vs `confirmed_at`:** Entry uses **bar `i` close**. Structural signal must be in the 5-bar window ending at `i`, measured on **`confirmed_at`**, not swing `bar_index`.

---

### Aggressive Ledge entry

**Window:** `session.py` helper e.g. `is_aggressive_ledge_window(ts_et) -> bool` for **09:25–10:00 ET** (D-12: every qualifying bar is eligible).

**Long (ENTRY-03):**

- Price **within 3 ticks** of LVN (REQ) — implement as distance from close or extreme to zone; planner should reference PROJECT.md for whether this uses **close** or **wick**; default: test both invariants.
- TPO bias **BULLISH** from `tpo.py` (locked at 9:30).
- Close **above** LVN + bullish candle.
- **No** structural confirmation requirement in REQ — do not add ISMT/SMT unless spec changes.
- Position size scaler **×0.5** applied at setup creation (Phase 5 consumes).

**Short (ENTRY-04):** Mirror.

**Session state (D-13, D-14):**

- `session_trades_taken: int` shared across models.
- `aggressive_lvn_suppressed: set[LVN_id]` (or midpoint key): when an aggressive ledge trade **opens** (or **closes** — CONTEXT says "fires and results in a trade"; planner: use **fill** moment) on LVN X, add X for rest of session.

---

### `TradeSetup` shape

Phase 5 (`EXEC-01`) defines fields; Phase 4 should **populate** them when emitting setups from `entry.py`:

- `setup_id`, `entry_price`, `stop_price`, `target_price` (TP1), `rr_ratio`, `direction`, `created_at` (bar index or timestamp), `setup_type` (`THREE_STEP` | `AGGRESSIVE_LEDGE`), `lvn_ref`, `ismt_or_smt_ref` (nullable for aggressive ledge if none), plus **`signal_source`** for SIG-03 / M2.

If `TradeSetup` lives in `position.py` stub from Phase 1, `entry.py` imports it and constructs instances **without** executing positions.

---

## Integration Points (Phases 1–3)

| Producer module | Consumed by | What crosses the boundary |
|-----------------|------------|---------------------------|
| `data_loader.py` | `smt.py`, `entry.py` (indirect) | Minute-aligned NQ+ES OHLCV + `is_synthetic` |
| `session.py` | `entry.py` | RTH vs pre-RTH, aggressive 9:25–10:00, EOD 15:45 gate for ENTRY-05 |
| `core.py` | `ismt.py`, `smt.py`, `entry.py` | `ATR_5`, `ATR_20` (synthetic-excluded per Phase 1) |
| `swings.py` | `ismt.py`, `smt.py` | Confirmed swings: `bar_index`, `confirmed_at`, price/extreme, direction |
| `tpo.py` | `entry.py` | Session bias enum locked at 9:30; NEUTRAL skips session (TPO-04) |
| `lvn.py` | `entry.py` | Zones: `low`, `high`, `valid`, identity for suppression |
| `single_prints.py` | `entry.py` | SP zones with `respected_overnight` for 3-step target gating |

**ARCHITECTURE.md drift:** Diagram mentions `smt.py` for "ISMT + SMT" and `signal.py` for entries. **Canonical modules per 01-CONTEXT D-10:** `ismt.py`, `smt.py`, `entry.py`. Planner should treat ARCHITECTURE as conceptual, file names as CONTEXT-locked.

---

## Edge Cases and Test Strategy

### Constructible datasets

| Scenario | What to prove | How |
|----------|---------------|-----|
| Correlation **0.65 vs 0.85** | SMT gated off/on at threshold 0.70 | Build 20 NQ+ES return vectors with known Pearson (spreadsheet or `numpy` simulation), assert `corrcoef` gate |
| ISMT sweep **1.9× vs 2.1× ATR20** | Boundary on `2×ATR20` filter | Flat price + synthetic swings; fix ATR20 constant |
| **confirmed_at** window | Close-back on `t+1` valid, at `t` invalid | Explicit OHLC sequence; expect no signal if using `bar_index` (negative control) |
| **5-bar recency** | Signal at `i-5` valid, `i-6` rejected | Inject signals with different `confirmed_at` |
| **Equal priority** | ISMT at 244, SMT at 245 → pick SMT at bar 247 | Fixture both lists |
| **Invalidation** | Later trade through SH1 marks bearish ISMT invalidated | Price path after signal |
| **Synthetic SMT** | ES synthetic bar in divergence window → no SMT | Tag `is_synthetic` |
| **>2 synthetic in 20** | Correlation skip | 3+ synthetic flags in window |
| **Approach vs chop** | Fails D-08 if one of prior 3 closes ≤ `LVN_high` | 4-bar micro-series |
| **Aggressive suppression** | Second aggressive attempt same LVN blocked | Session state test |

### Stubbing policy

- **Stub swings** as dataclasses with explicit `bar_index`, `confirmed_at`, `price`.
- **Stub bars** as `(open, high, low, close, is_synthetic)` arrays or simple objects.
- **Stub LVN/SP** as minimal objects with required fields (`low`, `high`, `valid`, `respected_overnight`).
- **Do not stub** `get_structural_confirmation` when testing entry — only when testing entry in isolation inject a fake confirmation provider.

### Invariants (high value)

- ∀ tests: no read of `bars[i+1]` at evaluation of bar `i`.
- ∀ SMT tests: correlation uses **exactly** past 20 returns including current bar's return definition consistently.
- ∀ ISMT tests: first bar checked for close-back is `SH2.confirmed_at + 1`.

---

## Validation Architecture

> Nyquist validation is **enabled** in `.planning/config.json` (`workflow.nyquist_validation: true`).

### Test framework

| Property | Value |
|----------|-------|
| Framework | pytest (not on PATH in dev environment as of research — use `python -m pytest` after `pip install pytest`) |
| Config | `pytest.ini` or `pyproject.toml` — **Wave 0**: add minimal config with `testpaths = tests` |
| Quick command | `python -m pytest tests/test_ismt.py tests/test_smt.py tests/test_entry.py -q --tb=short` |
| Full suite | `python -m pytest tests/ -q` |

### Phase requirements → tests map

| Req ID | Behavior | Test type | Automated command | File (Wave 0) |
|--------|----------|-----------|-------------------|---------------|
| ISMT-01/02 | Window + sweep + magnitude | unit | `python -m pytest tests/test_ismt.py -q` | `tests/test_ismt.py` |
| ISMT-03 | Dataclass fields populated | unit | same | same |
| SMT-02 | Correlation threshold + nan guard | unit | `python -m pytest tests/test_smt.py::test_correlation_gate -q` | `tests/test_smt.py` |
| SMT-03/04 | Divergence + ±3 bars | unit | `python -m pytest tests/test_smt.py -q` | same |
| SMT-05 | Signal payload | unit | same | same |
| SMT-01/07 | Synthetic suppression | unit | `python -m pytest tests/test_smt.py::test_synthetic_suppresses_smt -q` | same |
| SIG (D-04–D-06) | Recency + equal priority + invalidation | unit | `python -m pytest tests/test_structural_confirmation.py -q` | `tests/test_structural_confirmation.py` |
| ENTRY-01/02 | 3-step long/short composition | unit | `python -m pytest tests/test_entry_three_step.py -q` | `tests/test_entry_three_step.py` |
| ENTRY-03/04 | Aggressive window + suppression | unit | `python -m pytest tests/test_entry_aggressive.py -q` | `tests/test_entry_aggressive.py` |
| ENTRY-05 | Checklist rejects bad RR / SL / time / bias | unit | `python -m pytest tests/test_entry_checklist.py -q` | `tests/test_entry_checklist.py` |

### Nyquist-style practices for this phase

- **One logical behavior per test**; name tests `test_<req>_<scenario>`.
- **Golden vectors:** correlation and ISMT paths with hand-checked numeric expectations (avoid snapshotting huge outputs).
- **Property-style checks:** For random micro-paths (optional): monotonicity — moving `confirmed_at` older eventually drops out of 5-bar window.
- **Regression guard for superseded REQ:** Explicit test `test_sig_equal_priority_not_ismt_first` documenting D-04.

### Wave 0 gaps

- [ ] Create `tests/` package + shared `conftest.py` fixtures (`make_bars`, `make_swing`, `make_lvn`).
- [ ] Add pytest to dependency list / CI.
- [ ] No production code yet — tests drive first implementation of `ismt.py`, `smt.py`, `entry.py`.

### Sampling rate (recommended)

- **Per task commit:** module-scoped pytest for touched file (<30s).
- **Per wave merge:** full `tests/` suite.
- **Phase gate:** full suite green before `/gsd-verify-work`.

---

## Project Constraints (from `.cursor/rules/`)

**None verified** — `.cursor/rules/` is not present in the workspace. Follow Phase 1–4 CONTEXT decisions and REQUIREMENTS with CONTEXT precedence where they conflict.

---

## Common Pitfalls (Phase 4 focus)

| Pitfall | Mitigation |
|---------|------------|
| P3 intra-bar entry | Only call detectors after bar close; tests assert no future index reads |
| P7 SMT on synthetic | Central `smt_allowed(nq_bar, es_bar, window)` predicate |
| P2 swing lookahead | Only consume swings with `confirmed_at ≤ i` (SWING-04) |
| Wrong ISMT window anchor | Code review + dedicated test `test_ismt_uses_confirmed_at_not_bar_index` |
| REQ vs CONTEXT conflict (SIG) | Tests encode D-04; add REQUIREMENTS errata in planning |

---

## Open Questions

1. **Exact ISMT "within 10 bars" clocking** — between `SH1.confirmed_at` and `SH2.confirmed_at`, or involving `bar_index`?  
   - *Recommendation:* Use **confirmation indices** only; confirm against `PROJECT.md` and add one acceptance test.

2. **ATR20 index for sweep comparison** — at `SH2.confirmed_at`, signal completion bar, or max of extremes?  
   - *Recommendation:* At **signal completion bar**; document in PLAN for reproducibility.

3. **Aggressive ledge "within 3 ticks" reference price** — wick vs close vs either?  
   - *Recommendation:* Match PROJECT.md literal; if ambiguous, choose **closest approach distance** using low/high of current bar and document.

4. **`divergence_strength` formula** — not numerically specified in REQ.  
   - *Recommendation:* Define as normalized `(nq_move - es_move) / ATR20` at detection and freeze in tests.

---

## Sources

### Primary (HIGH)

- `.planning/phases/04-signal-generation-ismt-smt-entry/04-CONTEXT.md` — locked semantics (D-01–D-14)
- `.planning/REQUIREMENTS.md` — ISMT/SMT/ENTRY numeric thresholds
- `.planning/research/ARCHITECTURE.md`, `PITFALLS.md` — flow + P3/P7
- `.planning/phases/01-data-infrastructure-core-candle-math/01-CONTEXT.md` — modules, synthetic rules
- `.planning/phases/02-swing-detection-tpo-bias-engine/02-CONTEXT.md` — swing registry
- `.planning/phases/03-volume-profile-lvn-single-prints/03-CONTEXT.md` — LVN/SP objects
- [NumPy `corrcoef` documentation](https://numpy.org/doc/stable/reference/generated/numpy.corrcoef.html) — Pearson on 2×N arrays

### Secondary (MEDIUM)

- `.planning/research/STACK.md` — pandas/numpy policy

---

## Metadata

**Confidence breakdown:** Stack HIGH (stdlib + project docs); Architecture HIGH; Pitfalls HIGH; Numeric edge cases MEDIUM until PROJECT.md cross-check.

**Research date:** 2026-04-05  
**Valid until:** ~2026-05-05 (adjust if scipy/stats or data schema changes)

## RESEARCH COMPLETE
