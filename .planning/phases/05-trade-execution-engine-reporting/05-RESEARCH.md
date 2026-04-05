# Phase 05: Trade Execution Engine & Reporting — Research

**Researched:** 2026-04-05  
**Domain:** Deterministic bar-based execution (NQ), P&amp;L / commission accounting, Plotly reporting  
**Confidence:** HIGH for state machine + conflict rules (locked in CONTEXT); MEDIUM for same-bar entry timing and TP2-vs-SL ordering in `OPEN_PARTIAL` (not explicit in CONTEXT)

## Summary

Phase 5 turns frozen `TradeSetup` objects from Phase 4 into path-dependent outcomes: a **single open position** per session, bar-by-bar evaluation of limits/stops with **explicit precedence** (TP1 before SL; post-TP1 breakeven re-check on the **same bar** per D-06), hard stop on **body-in-LVN** at **bar close**, and EOD flat at **3:45 PM ET** at close. Reporting combines a **time-indexed candlestick** window (60 bars pre-entry, 30 post-exit, clipped to session bounds) with **horizontal volume-at-price** (SVP) aligned to the price scale, plus overlays for levels, LVN band, and fill markers.

**Primary recommendation:** Implement execution as a small **explicit state machine** (`Enum` + `Position.update(bar) -> list[FillEvent]`) with **one deterministic ordering function per bar**; persist **per-trade CSV append** and **per-trade HTML** under the run folder; drive all paths from **injectable `output_root`** so production uses `D:\Algorithms\Wicked Backtest Results\run_YYYYMMDD_HHMMSS\` and tests use `tmp_path`.

**Traceability note:** `REPORT-02` names `charts/trade_NNN.html` and `REPORT-03` names `trades.csv`; **Phase 05 CONTEXT (D-12–D-14) is the implementation source of truth** — CSV `backtest_results_{run_timestamp}.csv`, charts under `charts_{run_timestamp}/`, files `{trade_index}_{date}_{direction}_{setup_type}.html`. Update `REQUIREMENTS.md` in a docs pass to avoid AUDIT drift.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions (Implementation Decisions)

**Position state machine**

- **D-01:** Formal state machine with explicit states: `PENDING_FILL → OPEN_FULL → OPEN_PARTIAL → CLOSED`. Each bar's update is a clean switch on current state + bar events → new state. No conditional soup.
- **D-02:** One position at a time per session. A new setup is only evaluated when the current position reaches `CLOSED`. The strategy is a precision sniper approach — multiple simultaneous positions would require capital allocation, correlated drawdown handling, and directional conflict resolution, none of which are in scope.
- **D-03:** Daily limit of 3 trades applies globally across the session and across both setup types. Counter increments when a trade transitions to `OPEN_FULL`, not at setup creation.

**Fill price precision**

- **D-04:** Fill at exact target price for TP1 and TP2 (limit order modeling). Fill at exact SL price for stops. Bar close is irrelevant for these exits — they model limit/stop orders, not market-on-close.
- **D-05:** Conflict bar resolution (same bar hits both TP1 and SL): **TP1 wins.** Rationale: price must have traded through TP1 before reversing to hit SL. Implementation: always check TP1 before SL in bar evaluation order.
- **D-06:** After TP1 fires on a conflict bar: partial exit at TP1 price, SL moves to breakeven, then check whether the new breakeven SL was also hit on the same bar. If yes, remaining 40% exits at breakeven. This is the correct outcome — partial profits protected.
- **D-07:** Hard stop (body closes inside LVN): fills at bar close price (the only price that's meaningful since the condition is evaluated on bar close).
- **D-08:** EOD close (3:45 PM ET): fills at bar close price.

**Plotly chart design**

- **D-09:** Context window: 60 bars before entry, 30 bars after exit, capped at session boundaries.
- **D-10:** Overlays included:
  - Entry price: blue horizontal line
  - Stop loss: red horizontal line
  - TP1: green dashed horizontal line
  - TP2: green solid horizontal line
  - LVN zone: yellow shaded rectangle (low opacity) spanning full x-range
  - SVP: horizontal histogram on right side of chart (key visual — shows why the LVN exists)
  - Fill events (TP1 partial, TP2/SL close): vertical dashed lines
- **D-11:** Chart title format: `{instrument} | {date} | {direction} | {setup_type} | PnL: ${realized}`

**Incremental save & file structure**

- **D-12:** Per-trade append: write one CSV row immediately after each trade closes. A crash mid-session loses at most the current open position's outcome, never completed trades.
- **D-13:** CSV implementation: on first write — check file existence; if not, write with headers; if exists, open in append mode without headers. Keep an in-memory list as secondary buffer for summary statistics at the end.
- **D-14:** File naming convention:
  - CSV: `backtest_results_{run_timestamp}.csv` (multiple runs don't overwrite)
  - Charts directory: `charts_{run_timestamp}/`
  - Individual charts: `{trade_index}_{date}_{direction}_{setup_type}.html`
- **D-15:** All output to `D:\Algorithms\Wicked Backtest Results\run_YYYYMMDD_HHMMSS\` (per PROJECT.md).

### Claude's Discretion (Agent's Discretion)

- Position state machine implementation: Python `Enum` for states, single `update(bar)` method on the `Position` class that returns a list of fill events (0, 1, or 2 fills per bar possible on conflict bars).
- SVP histogram rendering: use Plotly `go.Bar` with horizontal orientation, secondary y-axis aligned to the candlestick price axis.

### Deferred Ideas (OUT OF SCOPE)

- None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SL-01 | Long SL = LVN_low − 0.5×ATR_5, snapped | Already in `entry.compute_sl_tp1_long`; execution consumes `TradeSetup.stop_price` |
| SL-02 | Short SL = LVN_high + 0.5×ATR_5, snapped | `compute_sl_tp1_short` |
| SL-03 | SL distance ≥ 4 ticks else reject | Pre-entry in `validate_pre_entry`; execution assumes valid setups only |
| SL-04 | SL distance ≤ 1.5×ATR_20 | Same |
| TP-01 | TP1 from nearest respected SP zone | `target_price` on `TradeSetup` = TP1 |
| TP-02 | TP2 = next SP or LVN per spec | **Gap:** `TradeSetup` today has only `target_price` (TP1) — compute TP2 at execution commit or extend dataclass |
| TP-03 | 60% off at TP1, SL → breakeven | State machine `OPEN_FULL → OPEN_PARTIAL` + `floor(full_size×0.60)` from `StrategyThresholds.take_profit_1_exit_pct` |
| TP-04 | TP2 closes remainder | `OPEN_PARTIAL → CLOSED` at exact TP2 |
| TP-05 | Hard stop: body inside LVN → exit at close | Bar-close check vs `setup.lvn_ref` zone; D-07 |
| TP-06 | EOD 3:45 PM ET force-flat at close | `StrategyThresholds.eod_force_close_time` + `session` time on bar |
| TP-07 | SL hit at exact SL price | D-04; intrabar touch via high/low |
| EXEC-01 | `TradeSetup` fields | Implemented in `src/position.py` (+ optional TP2 field or sidecar) |
| EXEC-02 | `TradeResult` + exit typing | New dataclass + enum for `exit_type` |
| EXEC-03 | Position sizing formula | `config.StrategyThresholds.account_size`, `risk_per_trade`, `InstrumentConfig.point_value` |
| EXEC-04 | Long/short gross P&amp;L | PITFALLS P4 polarity |
| EXEC-05 | Commission per fill event | PITFALLS C3/C4; see below |
| EXEC-06 | Max 3 trades/session | D-03 at `OPEN_FULL`; align with Phase 4 counter semantics |
| REPORT-01 | Plotly candlestick + levels | Plotly `go.Candlestick` + shapes/lines |
| REPORT-02 | Output under run folder | **Use D-14 names**, not `trade_NNN.html` |
| REPORT-03 | CSV one row per trade | D-12–D-13 append pattern |
| REPORT-04 | `summary.md` | May be minimal in Phase 5 if Phase 6 owns metrics; still emit stub or rollup from in-memory buffer |
| REPORT-05 | Incremental save | **Prefer D-12 per-trade**; if retaining REPORT-05 wording, treat as “incremental persistence during run” satisfied by per-trade CSV append |
</phase_requirements>

## Project Constraints (from .cursor/rules/)

- **None** — `.cursor/rules/` not present in this workspace. Follow existing `src/` patterns (dataclasses, `Literal` directions, frozen `InstrumentConfig`).

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.13 (observed) | Runtime | Repo environment |
| pandas | (project pin) | Bar rows as `Series` | Already used in `entry.py` |
| numpy | (project pin) | Numeric guards | Phase 3 profile arrays |
| plotly | **6.6.0** (PyPI latest; **6.5.2** installed) | HTML charts | De facto for interactive candlesticks |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | **9.0.2** (observed) | Validation Architecture | REQ mapping, regression |

**Installation:**

```bash
pip install "plotly>=6.5" pytest
```

**Version verification:** `pip index versions plotly` → latest **6.6.0** (2026-04-05); `pip show plotly` on dev machine → **6.5.2**.

## Architecture Patterns

### Recommended module layout

```
src/
├── position.py      # TradeSetup, Position, state Enum, update(bar), FillEvent, TradeResult
├── plotting.py      # build_trade_chart(trade, bars, profile, zones) -> go.Figure
├── reporting.py     # optional: RunWriter paths, CSV append, summary stub
└── backtest.py      # session loop: signal -> pending -> position updates -> report hooks
```

*(PROJECT.md lists `execution.py`; current code uses `position.py` — keep **one** canonical module to avoid duplicate types.)*

### State machine (D-01–D-08)

**States**

| State | Meaning |
|-------|---------|
| `PENDING_FILL` | Setup accepted; next bar(s) establish position at `entry_price` (planner: fix whether first risk bar is `created_at` or `created_at+1`; see Open Questions). |
| `OPEN_FULL` | Full size open; SL at `stop_price`; monitoring TP1, SL, hard stop, EOD. |
| `OPEN_PARTIAL` | ~40% remains after TP1; SL at **breakeven** (`entry_price`); monitoring TP2, SL, hard stop, EOD. |
| `CLOSED` | Flat; emit `TradeResult`, append CSV, write HTML. |

**Daily trade counter (D-03)**  
Increment when transitioning **into** `OPEN_FULL` (not when `TradeSetup` is constructed).

**Per-bar evaluation order (LONG; SHORT mirrors with high/low swapped)**

1. **Time:** If bar is EOD cutoff bar → `CLOSED` at **close** (D-08); else continue.  
2. **Hard stop (TP-05 / D-07):** If body ⊆ LVN zone → exit **remaining contracts** at **close**; `CLOSED`.  
3. If `OPEN_FULL`:  
   - **TP1 touch:** `high >= tp1` (limit sell) → partial fill at **exact tp1**; move SL to breakeven; state → `OPEN_PARTIAL`.  
   - **Else SL touch:** `low <= stop` → full exit at **exact stop**; `CLOSED`.  
   - **Conflict (D-05 / D-06):** If both TP1 and SL would trigger on same bar, **evaluate TP1 first**. After partial + breakeven SL, if `low <= entry` → second fill at **entry** same bar; `CLOSED`.  
4. If `OPEN_PARTIAL`:  
   - **TP2 touch** before **SL** (recommended symmetry with D-05; confirm in PLAN): `high >= tp2` → exit remainder at **tp2**; `CLOSED`.  
   - **Else** if `low <= entry` (breakeven) → exit remainder at **entry**; `CLOSED`.  
   - **Else** if `low <= old_stop` — N/A once at breakeven; use entry level only.

**Touch rules:** Use **high/low** vs limit/stop prices (AUDIT-07, D-04). Hard stop and EOD use **close** (D-07, D-08).

### TradeResult / FillEvent schema (EXEC-02, EXEC-05)

**FillEvent** (internal, list per `update`):

- `bar_index: int`  
- `kind: Literal["ENTRY","TP1_PARTIAL","TP2","SL","BREAKEVEN","HARD_STOP_LVN","EOD"]`  
- `price: float`  
- `contracts: int`  
- `direction: Literal["LONG","SHORT"]`  

**TradeResult** (persisted row + chart title):

- All **EXEC-01** fields carried from `TradeSetup` (including `lvn_id`, `position_size_scale`, `signal_source` if desired for ML later).  
- `tp2_price: float | None`  
- `exit_price_tp1: float | None`  
- `exit_price_tp2: float | None`  
- `exit_type: Enum` — map to EXEC-02 vocabulary: `FULL_TP | PARTIAL_TP | STOP | HARD_STOP | EOD` (and `TIMEOUT` if ever used).  
- `gross_pnl: float` — sum over legs: each leg `±(exit-entry)×contracts×point_value` with **short polarity** (P4).  
- `net_pnl: float` — `gross_pnl - total_commission`  
- `trade_index: int`, `session_date: str` — for D-14 filenames  

**Commission accounting (C3 / C4) — HIGH confidence**

- **Per event:** `commission_for_event = contracts_in_that_event * instrument.commission_per_side` (EXEC-05).  
- **Never** use a blind `×2×full_size` on the whole trade if there were **two** exit legs (TP1 + TP2/BREAKEVEN/SL) — that is C3/C4 territory.  
- **Correct total:** `comm_entry + sum(comm per exit event)`. Entry charges **full** contracts once; TP1 charges **contracts exited at TP1**; final exit charges **remaining contracts**.

### Plotly chart layering (D-09–D-11) and SVP

**Layout (align price scales)**  
CONTEXT discretion says “secondary y-axis”; **practical pattern (HIGH confidence):** `plotly.subplots.make_subplots(rows=1, cols=2, shared_yaxes=True, column_widths=[0.72, 0.28])` — left panel: candlestick vs **time**; right panel: `go.Bar(orientation="h", x=volumes, y=price_centers)` so **y is price**, matching the candlestick y-scale via `shared_yaxes`. Official reference: [Plotly subplots — shared y-axes](https://plotly.com/python/subplots/), [multiple axes](https://plotly.com/python/multiple-axes/) if overlay preferred.

**Candlestick:** `go.Candlestick(x=..., open=..., high=..., low=..., close=...)` — [Plotly candlestick](https://plotly.com/python/candlestick-charts/).

**Overlays (D-10):**

- **Horizontal levels:** `fig.add_hline(...)` or `go.Scatter(mode="lines", x=[x0,x1], y=[p,p])` clipped to window.  
- **LVN zone:** `layout.shapes` `type="rect"`, `y0/y1` = zone bounds, `x0/x1` = first/last timestamp in **chart window**, low opacity yellow.  
- **Fills:** vertical `shapes` or `add_vline` at event bar time, dashed.  
- **Title (D-11):** `fig.update_layout(title=...)`.

**SVP data:** Use frozen `VolumeProfile` (`volumes`, `base_price`, `tick_size`) from Phase 3; map nonzero indices to `(price, vol)` for bars.

### Output paths: production vs tests

| Mode | Root | Layout |
|------|------|--------|
| Production | `D:\Algorithms\Wicked Backtest Results\run_YYYYMMDD_HHMMSS\` (D-15) | `backtest_results_{run}.csv`, `charts_{run}/`, HTML per D-14 |
| Tests | `tmp_path` / pytest monkeypatch | Same **relative** layout under tmp; never assert on `D:\` |

**Implementation:** `RunPaths(root: Path)` built from `AppConfig.output_dir` or env override e.g. `WICKED_OUTPUT_ROOT` for CI. Default in `config.yaml` should match D-15 on dev machines.

**Environment check (this machine):** `D:\` and `D:\Algorithms\Wicked Backtest Results` **exist** — local runs OK; CI agents may lack `D:\` → tests **must** inject tmp roots.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTML interactive charts | Matplotlib static only | Plotly `go.Candlestick` + subplots | REPORT-01, zoom/pan |
| Ad-hoc CSV append | Manual string concat | `csv.DictWriter` + `open(..., "a", newline="")` + header-once | D-13, Windows newlines |
| Multi-axis alignment | Guess y-range | `make_subplots(..., shared_yaxes=True)` | SVP lines up with price |
| Commission | Single 2× formula | Per-event legs | C3/C4 |

**Key insight:** The bugs are **silent** (P4, C3, C4); tests must pin **numeric** expectations on short + partial trades.

## Common Pitfalls

### P4 — Short P&amp;L polarity
**What goes wrong:** Gross P&amp;L sign inverted for shorts.  
**How to avoid:** `LONG: (exit-entry)×...`; `SHORT: (entry-exit)×...` (PITFALLS P4).  
**Warning signs:** Short-only backtest with “too good” equity.

### C3 / C4 — Commission
**What goes wrong:** Double-counting one round-trip or forgetting second exit leg.  
**How to avoid:** Sum commissions per **fill event** (entry + each exit).  
**Warning signs:** Net ≈ gross − 2×full×comm on partial trades.

### Same-bar sequencing
**What goes wrong:** SL evaluated before TP1; wrong on conflict bar.  
**How to avoid:** Strict ordering D-05/D-06; unit test synthetic OHLC bar.

### Hard stop vs limit touch
**What goes wrong:** Using bar low for LVN body rule.  
**How to avoid:** Body = interval `[min(O,C), max(O,C)]` fully inside zone; exit **close** (D-07).

### TP2 missing on `TradeSetup`
**What goes wrong:** TP2 undefined at execution.  
**How to avoid:** Compute during setup build or attach `tp2_price` when promoting setup to `PENDING_FILL`.

## Code Examples

### Shared-y histogram + candlestick (pattern)

```python
# Source: https://plotly.com/python/subplots/ (shared_yaxes), https://plotly.com/python/candlestick-charts/
import plotly.graph_objects as go
from plotly.subplots import make_subplots

fig = make_subplots(
    rows=1,
    cols=2,
    shared_yaxes=True,
    column_widths=[0.72, 0.28],
    horizontal_spacing=0.02,
)
fig.add_trace(
    go.Candlestick(x=times, open=o, high=h, low=l, close=c, name="NQ"),
    row=1,
    col=1,
)
fig.add_trace(
    go.Bar(x=volumes, y=price_levels, orientation="h", name="SVP", marker_color="rgba(100,100,200,0.55)"),
    row=1,
    col=2,
)
fig.update_layout(xaxis_rangeslider_visible=False, title_text="NQ | ...")
```

### Short gross leg (P4)

```python
# Source: .planning/research/PITFALLS.md (P4)
if direction == "LONG":
    gross = (exit_price - entry_price) * contracts * point_value
else:
    gross = (entry_price - exit_price) * contracts * point_value
```

### Commission per event (C4)

```python
# Source: .planning/research/PITFALLS.md (C4) + EXEC-05
total_comm = 0
total_comm += entry_contracts * commission_per_side
total_comm += tp1_contracts * commission_per_side
total_comm += final_contracts * commission_per_side
net_pnl = gross_pnl - total_comm
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single commission ×2 | Per fill event | Locked in EXEC-05 + C4 | Correct partial exits |
| REPORT-02 flat `trade_NNN` | Descriptive filenames D-14 | Phase 05 CONTEXT | Traceable artifacts |

**Deprecated/outdated:** `REQUIREMENTS.md` REPORT-02 path vs D-14 — treat CONTEXT as authoritative for implementation.

## Open Questions

1. **First bar of open position:** Does risk/TP evaluation start on `created_at` or `created_at + 1`?  
   - *What we know:* Setups use bar **close** as entry price.  
   - *Recommendation:* PLAN picks one; add test so same-bar stop cannot sneak lookahead if disallowed.

2. **TP2 vs SL on same bar in `OPEN_PARTIAL`:** Mirror “target before stop”?  
   - *What we know:* D-05 only names TP1 vs SL.  
   - *Recommendation:* Default **TP2 before breakeven SL**; document in PLAN.

3. **`summary.md` (REPORT-04) depth:** Full institutional block vs stub until Phase 6?  
   - *Recommendation:* Phase 5 writes **run metadata + trade count + total P&amp;L**; Phase 6 expands Sharpe/Sortino/PF.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python | Runtime | ✓ | 3.13 (observed) | — |
| plotly | REPORT-01 | ✓ | 6.5.2 installed; 6.6.0 PyPI | `pip install -U plotly` |
| pytest | Validation | ✓ | 9.0.2 | — |
| `D:\Algorithms\Wicked Backtest Results` | D-15 local | ✓ (this machine) | — | `tmp_path` / env override in CI |

**Missing dependencies with no fallback:** None for core library work.

**Missing dependencies with fallback:** `D:\` on CI → inject `output_root` under `tmp_path`.

## Validation Architecture

> `workflow.nyquist_validation` is **true** in `.planning/config.json` — this section is **mandatory**.

### Test framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.x |
| Config file | none — use `tests/conftest.py` at repo or `tests/phase05/conftest.py` |
| Quick run command | `pytest tests/phase05 -q --tb=short -x` |
| Full suite command | `pytest tests -q` |

### Phase requirements → test map (automated)

| Req ID | Behavior | Test type | Automated command | File exists? |
|--------|----------|-----------|-------------------|--------------|
| SL-01–SL-04 | Stop price tick snap + reject too tight/wide | unit (indirect via setup builder) | `pytest tests/phase04/test_entry_checklist.py -q` | ✅ existing Phase 4 |
| TP-01–TP-02 | TP1/TP2 selection rules | unit | `pytest tests/phase05/test_tp_levels.py::test_tp2_fallback_lvn -q` | ❌ Wave 0 |
| TP-03–TP-07 | Partial 60%, breakeven, TP2, hard stop body, EOD, SL exact | unit | `pytest tests/phase05/test_position_machine.py -q` | ❌ Wave 0 |
| EXEC-01–EXEC-02 | TradeSetup → TradeResult field carry + exit_type | unit | `pytest tests/phase05/test_trade_result_schema.py -q` | ❌ Wave 0 |
| EXEC-03 | `floor` sizing, min 1, scale 0.5 aggressive | unit | `pytest tests/phase05/test_position_sizing.py -q` | ❌ Wave 0 |
| EXEC-04 | Short P&amp;L known numeric | unit | `pytest tests/phase05/test_pnl_short.py -q` | ❌ Wave 0 |
| EXEC-05–EXEC-06 | Commission 2-leg + 3-leg; daily cap at OPEN_FULL | unit | `pytest tests/phase05/test_commission.py` + `test_daily_limit.py` | ❌ Wave 0 |
| REPORT-01 | Figure has candlestick + hline traces | smoke | `pytest tests/phase05/test_plotting_smoke.py -q` | ❌ Wave 0 |
| REPORT-02–D-14 | HTML written with expected filename pattern | integration tmp_path | `pytest tests/phase05/test_report_paths.py -q` | ❌ Wave 0 |
| REPORT-03 | CSV append + header once | integration tmp_path | `pytest tests/phase05/test_csv_incremental.py -q` | ❌ Wave 0 |
| REPORT-04 | `summary.md` created | smoke tmp_path | `pytest tests/phase05/test_summary_stub.py -q` | ❌ Wave 0 |
| REPORT-05 | Per-trade persistence (D-12) | integration | covered by `test_csv_incremental.py` | ❌ Wave 0 |

### Sampling rate

- **Per task commit:** `pytest tests/phase05 -q -x` (focused module if touching one area).  
- **Per wave merge:** `pytest tests -q`.  
- **Phase gate:** full `pytest tests` green before `/gsd-verify-work`.

### Wave 0 gaps

- [ ] Create `tests/phase05/` package mirroring `tests/phase04/`.  
- [ ] `tests/phase05/conftest.py` — factories for `TradeSetup`, synthetic bars, `VolumeProfile` stub.  
- [ ] `tests/phase05/test_position_machine.py` — conflict bar D-05/D-06 matrix (LONG and SHORT).  
- [ ] `tests/phase05/test_commission.py` — one partial + one full exit; assert net vs gross.  
- [ ] `tests/phase05/test_plotting_smoke.py` — `fig.to_html()` no throw; assert trace count ≥ N.  
- [ ] `tests/phase05/test_report_paths.py` — filename `{trade_index}_{date}_{direction}_{setup_type}.html`.

*(SL requirements are enforced at entry construction today; Phase 5 tests should still **re-assert** stop/TP touch math if execution duplicates snap logic.)*

## Sources

### Primary (HIGH confidence)

- `.planning/phases/05-trade-execution-engine-reporting/05-CONTEXT.md` — D-01–D-15  
- `.planning/REQUIREMENTS.md` — SL/TP/EXEC/REPORT IDs  
- `.planning/research/PITFALLS.md` — P4, C2, C3, C4, C7  
- [Plotly Python candlestick](https://plotly.com/python/candlestick-charts/)  
- [Plotly Python subplots / shared y-axes](https://plotly.com/python/subplots/)  
- [Plotly Python multiple axes](https://plotly.com/python/multiple-axes/)

### Secondary (MEDIUM confidence)

- `.planning/research/ARCHITECTURE.md` — RTH / output layer naming (`execution.py` vs `position.py` drift)  
- `.planning/PROJECT.md` — output tree (update chart filenames to D-14 when editing)

### Tertiary (LOW confidence)

- Intrabar path assumptions when both TP2 and SL “touch” — not specified; symmetric TP2-before-SL recommended for PLAN sign-off.

## Metadata

**Confidence breakdown:**

- Standard stack: **HIGH** — plotly verified via pip/PyPI; patterns from official Plotly docs.  
- Architecture: **HIGH** for state ordering locked in CONTEXT; **MEDIUM** for first-bar-open and TP2 conflict.  
- Pitfalls: **HIGH** — P4/C3/C4 explicitly documented in project research.

**Research date:** 2026-04-05  
**Valid until:** ~2026-05-05 (plotly 6.x stable); revisit if execution module split.

---

## RESEARCH COMPLETE

**Phase:** 05 — Trade Execution Engine & Reporting  
**Confidence:** **HIGH** (with noted MEDIUM gaps above)

### Key Findings

1. **Explicit per-bar ordering** implements D-05/D-06: TP1 → (breakeven SL) → remaining flat same bar if needed.  
2. **Commission** must be summed **per fill event**; never a single `2×full×comm` on partial strategies (C3/C4).  
3. **SVP + candles:** `make_subplots(1×2, shared_yaxes=True)` + `go.Bar(orientation="h")` satisfies “histogram at price” better than volume-scaled secondary y on one panel.  
4. **Output:** D-14 naming supersedes REPORT-02; inject `output_root` for tests.  
5. **TP2** is not on `TradeSetup` yet — extend or compute before `PENDING_FILL`.

### File Created

`.planning/phases/05-trade-execution-engine-reporting/05-RESEARCH.md`

### Confidence Assessment

| Area | Level | Reason |
|------|-------|--------|
| Standard stack | HIGH | pip + Plotly official docs |
| Architecture | HIGH / MEDIUM | CONTEXT-locked machine; two edge policies TBD |
| Pitfalls | HIGH | PITFALLS.md + REQ AUDIT items |

### Open Questions

- First bar of open position indexing.  
- TP2 vs SL same-bar precedence in `OPEN_PARTIAL`.  
- Depth of `summary.md` in Phase 5 vs 6.

### Ready for Planning

Research complete. Planner can now create `PLAN.md` files.
