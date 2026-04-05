# Phase 3: Volume Profile + LVN + Single Prints - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-05
**Phase:** 03-volume-profile-lvn-single-prints
**Areas discussed:** Volume profile data structure, LVN smoothing, Multi-session confluence storage, Single print detection timing

---

## Volume Profile Data Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Numpy array (tick-indexed) | O(1) array lookup, contiguous memory, vectorized ops | ✓ |
| Python dict | `{price: volume}`, simple but cache-unfriendly at scale (PERF1) | |
| Both offered | Array as perf path, dict as fallback | |

**User's choice:** Numpy array as the ONLY path
**Notes:** "Don't offer both." Dict at 4M rows is the flagged pitfall. Pre-allocate with `session_low - 50pts` to `session_high + 50pts`. Store `base_price` for bidirectional conversion. One array per session in `VolumeProfile` object, built once, never mutated.

---

## LVN Smoothing Implementation

| Option | Description | Selected |
|--------|-------------|----------|
| Centered 3-tick rolling average | `(raw[i-1] + raw[i] + raw[i+1]) / 3` | ✓ |
| Left-aligned (trailing) | `(raw[i-2] + raw[i-1] + raw[i]) / 3` | |

**User's choice:** Centered rolling average
**Notes:** Profile is frozen — no future data concern. Trailing window shifts trough location left by one tick, identifying minimum late relative to true thin-node center. Boundary: use raw values at edges.

---

## Multi-Session LVN Confluence Storage

| Option | Description | Selected |
|--------|-------------|----------|
| Distilled midpoints only | List of 5-20 floats per session in rolling 2-element buffer | ✓ |
| Full SVP arrays cached | Keep prior 2 sessions' numpy arrays (~MB each) | |

**User's choice:** Distilled midpoints only
**Notes:** Full SVP per session is several MB. Filter only needs "is there a midpoint within ±2 ticks of X?" — a linear scan over 5-20 floats. Two-element rolling buffer, evict oldest at session boundary, free SVP array after distillation.

---

## Single Print Detection Timing

| Option | Description | Selected |
|--------|-------------|----------|
| Prior session's TPO → overnight respect check | Detect from completed session, validate during overnight | ✓ |
| Current pre-market TPO | Detect and check within same session | |

**User's choice:** Prior session's TPO, checked against current overnight
**Notes:** "You can't use prints from a session that hasn't finished yet as targets for trades that happen during that same session." At 18:00 ET close: freeze TPO → detect SPs → store. During 18:00→09:29: run respect check bar-by-bar. By 09:29: `respected_overnight` flag is final and locked.

---

## Agent's Discretion

- `VolumeProfile` object encapsulates array + base_price + accessors
- LVN zone object carries full metadata including invalidation reason
- Gap open invalidation checked once at first RTH bar

## Deferred Ideas

None — discussion stayed within phase scope.
