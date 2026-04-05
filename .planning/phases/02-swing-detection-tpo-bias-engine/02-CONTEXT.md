# Phase 2: Swing Detection & TPO Bias Engine - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement hindsight-free swing high/low detection with mandatory confirmation delay and an incremental registry, and compute pre-market TPO bias from 30-minute bars locked at 9:30 AM ET. Swings and TPO bias are consumed by Phase 4 (signal generation) — this phase produces the detection primitives only.

</domain>

<decisions>
## Implementation Decisions

### Swing Registry Design
- **D-01:** Session-scoped registry with a prior-session tail buffer. Two separate lists: `current_session_swings` (grows live, cleared at 18:00 ET session boundary) and `prior_session_tail` (frozen snapshot of the last 5 confirmed swings from the prior session).
- **D-02:** At session boundary: snapshot the last 5 confirmed swings from the dying session into `prior_session_tail`, then clear `current_session_swings`. This captures swings that formed in the final minutes of one session and could be referenced at the open of the next.
- **D-03:** Query pattern: when signal logic asks for "last N confirmed swings in direction X," merge both lists, sort by `confirmed_at`, and take the most recent N. Simple list data structure — a session produces at most a few hundred swings, so O(n) lookup cost is negligible.

### TPO Letter Assignment Granularity
- **D-04:** Assign TPO letters at tick-level granularity (0.25 points for NQ). Every price tick visited during a 30-minute period gets a TPO letter. Tick-level ensures no ambiguity at the session midpoint — a 1-point bucket straddling the midpoint would get arbitrarily assigned to one side. Finer granularity produces a smoother, more stable upper/lower ratio.

### TPO Pre-Market Window
- **D-05:** Use the full overnight window: 18:00 ET → 09:29 ET (~15.5 hours). No subset (Asia-only, London-only, etc.). Rationale: TPO bias measures where the market spent time overnight — a full window showing 60% upper is a stronger signal (sustained acceptance) than a truncated window showing the same ratio (brief session noise).

### 30-Minute Bar Aggregation
- **D-06:** Anchor resample to fixed 18:00 ET origin, regardless of when the first actual bar arrives. Periods are always 18:00–18:30, 18:30–19:00, etc. This ensures consistent, comparable TPO letter counts across all sessions.
- **D-07:** Use `resample('30min', label='left', closed='left', origin=session_start_18h)` in pandas. If a 30-minute period has no bars, it contributes zero TPO count — do NOT fill it synthetically.
- **D-08:** A bar arriving at 18:02 falls into the 18:00–18:30 bucket. Anchoring to first-available-bar would produce non-comparable period boundaries across sessions.

### Agent's Discretion
- Swing detection implementation uses incremental detection per PERF4 pitfall recommendation — only check if bar `N-lookback` ago qualifies as a new swing at each new bar arrival, rather than re-scanning the entire session.
- TPO bias lock timing: computed and frozen at 09:30 AM ET. Not recomputed during RTH. Stored as a session-level attribute.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Strategy Specification
- `.planning/REQUIREMENTS.md` — SWING-01 through SWING-05, TPO-01 through TPO-05
- `.planning/PROJECT.md` — Swing detection params (±5 bar lookback, 4-tick min threshold), TPO bias thresholds (55%/45%)

### Architecture & Design
- `.planning/research/ARCHITECTURE.md` — Session phases (overnight → pre-market → RTH), swing detection placement in RTH loop
- `.planning/research/PITFALLS.md` — P2 (symmetric swing lookahead — the primary correctness risk), P6 (resample label lookahead), PERF4 (per-bar swing recalculation)

### Prior Phase Context
- `.planning/phases/01-data-infrastructure-core-candle-math/01-CONTEXT.md` — D-02 (ET-canonical timestamps), D-05 (synthetic bar exclusion from ATR), D-10 (module ownership: `swings.py`, `tpo.py`, `session.py`, `core.py`)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Phase 1 provides: `session.py` (window definitions), `core.py` (ATR), `data_loader.py` (synchronized bar stream)
- `swings.py` and `tpo.py` stubs will exist from Phase 1 (D-09)

### Established Patterns
- Session-scoped state cleared at 18:00 ET boundaries (from Phase 1 session architecture)
- Incremental computation preferred over full-session recalculation (PERF4)

### Integration Points
- `swings.py` feeds into `ismt.py` and `smt.py` (Phase 4)
- `tpo.py` feeds into `entry.py` (Phase 4) as a session-level gate
- Both modules consume bars from `data_loader.py` synchronized stream

</code_context>

<specifics>
## Specific Ideas

- User explicitly defined the two-list swing registry pattern: `current_session_swings` + `prior_session_tail` (last 5 frozen)
- User specified `origin` parameter for pandas resample to anchor at 18:00 ET
- User was clear that empty 30-min periods contribute zero TPO — no synthetic fill

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-swing-detection-tpo-bias-engine*
*Context gathered: 2026-04-05*
