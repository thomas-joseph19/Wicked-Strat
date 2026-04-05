# Phase 4: Signal Generation (ISMT + SMT + Entry) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-05
**Phase:** 04-signal-generation-ismt-smt-entry
**Areas discussed:** ISMT confirmation window, Signal priority/recency, LVN approach definition, Aggressive ledge window behavior

---

## ISMT Confirmation Window Start

| Option | Description | Selected |
|--------|-------------|----------|
| `SH2.confirmed_at` | Window starts after swing is mathematically confirmed | ✓ |
| `SH2.bar_index` | Window starts from the actual swing high bar (lookahead) | |

**User's choice:** `SH2.confirmed_at` — no lookahead
**Notes:** "Starting from bar_index is lookahead — you are checking for a close below SH1 before you legally know SH2 exists." Window opens bar after `confirmed_at`, closes 3 bars later. Some signals will be stale by confirmation time and fail the recency check — correct behavior. "Better to miss a signal than to act on one that required future knowledge."

---

## Signal Priority (get_structural_confirmation)

| Option | Description | Selected |
|--------|-------------|----------|
| SMT > ISMT (dual-instrument stronger) | SMT always wins when both present in 5-bar window | ✓ |
| ISMT > SMT (original spec SIG-02) | ISMT takes priority per original requirements | |
| Most recent signal wins | Regardless of type, take the freshest | |

**User's choice:** SMT > ISMT — **OVERRIDES original spec SIG-02 and PROJECT.md**
**Notes:** "SMT has external confirmation from a second instrument — it's a structurally stronger signal by construction." Stale SMT (5 bars ago, within window) beats fresh ISMT (1 bar ago). Exception: if SMT source swings are invalidated (price traded through), discard SMT and fall back to ISMT. 5-bar window measured backwards from current eval bar, inclusive.

---

## "Approaches LVN" Definition

| Option | Description | Selected |
|--------|-------------|----------|
| Directional approach (3 bars) + touch | Prior 3 closes above zone AND current bar within 3 ticks | ✓ |
| Current bar touches zone | Any bar touching LVN triggers approach | |
| Price within N ticks for N bars | Proximity duration threshold | |

**User's choice:** Two-part condition: touch (low ≤ LVN_high + 3 ticks) AND directional (prior 3 closes strictly above LVN_high)
**Notes:** Prevents firing when price is chopping around zone or sitting inside/below. Second line of defense beyond LVN consolidation invalidation. Current bar does NOT need to close above LVN at approach time — close requirement is the entry trigger, not the approach detector.

---

## Aggressive Ledge Window Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Every qualifying bar is a candidate | Global daily limit applies, per-LVN suppression after first trade | ✓ |
| First qualifying bar only | Special-case the first match in window | |

**User's choice:** Every qualifying bar, but suppress per-LVN after first trade
**Notes:** "If price dips to an LVN at 9:31, bounces, dips again at 9:44 and produces a cleaner rejection, the 9:44 bar is a better setup and you want to take it." Daily max-3 limit applies globally across both setup types. Once a specific LVN produces a trade, suppress it for aggressive ledge entries for the rest of the session.

---

## Agent's Discretion

- SMT correlation: `numpy.corrcoef` on 20-bar return arrays
- ISMT/SMT carry `invalidated` flag for post-signal swing invalidation

## Deferred Ideas

None — discussion stayed within phase scope.
