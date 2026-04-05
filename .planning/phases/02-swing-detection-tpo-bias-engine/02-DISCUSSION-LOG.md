# Phase 2: Swing Detection & TPO Bias Engine - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-05
**Phase:** 02-swing-detection-tpo-bias-engine
**Areas discussed:** Swing registry design, TPO letter granularity, TPO pre-market window, 30-min bar aggregation

---

## Swing Registry Design

| Option | Description | Selected |
|--------|-------------|----------|
| Session-only with tail buffer | Clear at boundary, snapshot last 5 swings as `prior_session_tail` | ✓ |
| Session-only, no carry-over | Clear completely at 18:00 ET | |
| Cross-session persistence | Keep full swing history across sessions | |

**User's choice:** Session-only with tail buffer (last 5 confirmed swings from prior session)
**Notes:** Two lists: `current_session_swings` (live, cleared at 18:00) + `prior_session_tail` (frozen last 5). Merge and sort by `confirmed_at` when querying. Simple list — few hundred swings per session max. ISMT/SMT only looks back a small number of bars, so 5 tail swings captures the cross-session edge case.

---

## TPO Letter Assignment Granularity

| Option | Description | Selected |
|--------|-------------|----------|
| Every tick (0.25 pt) | Maximum resolution, unambiguous midpoint placement | ✓ |
| Every point (1.0 pt) | Coarser, potential midpoint ambiguity | |
| Every N ticks | Configurable bucket size | |

**User's choice:** Every tick (0.25 pt)
**Notes:** At coarser granularity, a bucket straddling the session midpoint gets arbitrarily assigned. Tick-level places every level unambiguously. Finer granularity = smoother, more stable bias reading.

---

## TPO Pre-Market Window

| Option | Description | Selected |
|--------|-------------|----------|
| Full 18:00 → 09:29 ET | Complete overnight window (~15.5 hours) | ✓ |
| Asia session only | ~18:00 → 02:00 ET subset | |
| London session only | ~02:00 → 08:00 ET subset | |
| Asia + London | Multi-session subset | |

**User's choice:** Full 18:00 → 09:29 ET
**Notes:** Measures sustained overnight acceptance, not brief session noise. A full window showing 60% upper is stronger signal than truncated window. Truncating introduces arbitrary session importance choices.

---

## 30-Minute Bar Aggregation Origin

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed 18:00 ET anchor | Periods always 18:00-18:30, 18:30-19:00, etc. | ✓ |
| First-available-bar anchor | Periods start from first real bar timestamp | |

**User's choice:** Fixed 18:00 ET anchor
**Notes:** Consistent, comparable boundaries across all sessions. First-available-bar would produce non-comparable periods across days. Empty periods contribute zero TPO count — no synthetic fill. `resample('30min', label='left', closed='left', origin=...)`.

---

## Agent's Discretion

- Incremental swing detection (check bar N-lookback ago only, per PERF4 pitfall)
- TPO bias frozen at 09:30 AM as session-level attribute

## Deferred Ideas

None — discussion stayed within phase scope.
