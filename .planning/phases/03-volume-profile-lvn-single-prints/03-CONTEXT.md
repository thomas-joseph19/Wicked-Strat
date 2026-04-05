# Phase 3: Volume Profile + LVN + Single Prints - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Build Session Volume Profiles (SVP) from pre-RTH bars using numpy arrays, detect LVN zones via smoothed local minima, apply all 4 LVN filters (POC proximity, multi-session confluence, minimum separation, real-time consolidation invalidation), detect single print zones from the prior session's TPO profile, and verify overnight respect for target selection.

</domain>

<decisions>
## Implementation Decisions

### Volume Profile Data Structure
- **D-01:** Numpy array indexed by tick number — the ONLY implementation path. No dict fallback. `tick_idx = round((price - base_price) / tick_size)` for O(1) lookup, contiguous memory, and vectorized smoothing/argmax passes.
- **D-02:** Pre-allocate the array with a fixed price range: `session_low - 50pts` to `session_high + 50pts`, computed from a first pass over the pre-RTH bars. Store `base_price` (lowest price in the array) alongside the array for bidirectional conversion: `idx = round((price - base_price) / tick_size)` and `price = base_price + idx * tick_size`.
- **D-03:** One array per session, encapsulated in a `VolumeProfile` object. Built once from pre-RTH bars, never mutated after construction.

### LVN Smoothing
- **D-04:** Centered 3-tick rolling average on the frozen profile. `smoothed[i] = (raw[i-1] + raw[i] + raw[i+1]) / 3`. The profile is fully frozen before smoothing runs — no future data concern.
- **D-05:** Boundary handling: use raw values at index 0 and index -1 (or reflect). Extreme price edges are never LVNs in practice, so boundary handling is non-critical.
- **D-06:** Centered smoothing is required because a trailing window shifts trough locations left, identifying the minimum one tick late relative to the true thin-node center.

### Multi-Session LVN Confluence Storage
- **D-07:** Store only distilled LVN midpoints from the prior 2 sessions — NOT full SVP arrays. A list of midpoints per session (typically 5–20 floats) is sufficient to answer "is there a midpoint within ±2 ticks of X?" via simple linear scan.
- **D-08:** Two-element rolling buffer: at each session boundary, evict the oldest session's midpoints, push the new session's surviving LVN midpoints. Free the SVP numpy array after distillation.
- **D-09:** If a downstream need for full prior SVPs ever emerges, that's the time to reconsider. For this filter: midpoints only.

### Single Print Detection Timing
- **D-10:** Single prints are detected from the **prior completed session's** TPO profile. At session close (18:00 ET), freeze the outgoing session's TPO, detect its SP zones, and store them.
- **D-11:** During the overnight window (18:00 → 09:29 ET), run the overnight respect check against those stored zones bar-by-bar. By 09:29 ET, each SP zone has a final, locked `respected_overnight` flag.
- **D-12:** The current pre-market window does NOT generate new single prints — it only validates or invalidates the prior session's prints through the respect check. You cannot use prints from a session that hasn't finished yet as targets for trades during that same session.

### Agent's Discretion
- `VolumeProfile` object design: encapsulates the numpy array, `base_price`, `tick_size`, POC, VAH, VAL, and provides `get_volume_at(price)` and `get_price_at(idx)` accessor methods.
- LVN zone object carries: `low`, `high`, `midpoint`, `width`, `strength`, `valid` flag, `invalidation_reason`.
- Gap open invalidation (LVN-05) is checked once at the first RTH bar — not repeatedly.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Strategy Specification
- `.planning/REQUIREMENTS.md` — SVP-01 through SVP-06, LVN-01 through LVN-06, SP-01 through SP-05
- `.planning/PROJECT.md` — LVN detection formula, single print criteria, overnight respect definition

### Architecture & Design
- `.planning/research/ARCHITECTURE.md` — Pre-market phase flow (SVP → LVNs → Filtered LVNs → SP zones), data flow diagram
- `.planning/research/PITFALLS.md` — P1 (VP lookahead bias — freeze at 09:30), P5 (LVN carry-over), PERF1 (dict vs array — resolved: array only)

### Prior Phase Context
- `.planning/phases/01-data-infrastructure-core-candle-math/01-CONTEXT.md` — D-02 (ET timestamps), D-10 (`volume_profile.py`, `lvn.py`, `single_prints.py` module ownership)
- `.planning/phases/02-swing-detection-tpo-bias-engine/02-CONTEXT.md` — D-04 (tick-level TPO granularity), D-06 (18:00 ET resample anchor)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Phase 1 provides: `session.py` (session boundaries, pre-RTH window), `data_loader.py` (bar stream), `config.py` (tick_size, thresholds)
- Phase 2 provides: `tpo.py` (TPO profile at tick granularity — SP detection reuses this)
- `volume_profile.py`, `lvn.py`, `single_prints.py` stubs from Phase 1

### Established Patterns
- Session-scoped state cleared at 18:00 ET (Phase 1 architecture)
- Numpy arrays preferred over dicts for price-indexed data (this phase establishes the pattern)
- Prior-session data stored as distilled summaries, not full objects (midpoints, not full SVPs)

### Integration Points
- `volume_profile.py` → `lvn.py` (LVN candidates from SVP)
- `single_prints.py` → `entry.py` Phase 4 (respected SP zones as targets)
- `lvn.py` → `entry.py` Phase 4 (filtered, valid LVN zones as entry triggers)
- `lvn.py` consumes real-time bar updates during RTH for consolidation invalidation (LVN-04)

</code_context>

<specifics>
## Specific Ideas

- User specified exact array pre-allocation formula: `session_low - 50pts` to `session_high + 50pts`
- User specified exact centered smoothing formula: `smoothed[i] = (raw[i-1] + raw[i] + raw[i+1]) / 3`
- User explicitly chose minimal memory footprint: free SVP arrays after distilling midpoints
- User confirmed the only valid SP detection order: prior session TPO → overnight respect check → locked flags before RTH

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-volume-profile-lvn-single-prints*
*Context gathered: 2026-04-05*
