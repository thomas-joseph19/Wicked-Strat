# Phase 1: Data Infrastructure & Core Candle Math - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-05
**Phase:** 01-data-infrastructure-core-candle-math
**Areas discussed:** Data loading strategy, Timestamp storage, Synthetic bar fill policy, Config design, Module structure

---

## Data Loading Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Eager (full RAM) | Load both parquets entirely into memory at startup, build session index once | ✓ |
| Lazy/chunked | Stream or chunk-load by session/year, re-seek as needed | |

**User's choice:** Eager — full RAM load
**Notes:** Both files fit comfortably (~300MB working set at float32). Strategy needs random access across full history for multi-session LVN confluence lookups and MC chunk sampling. Lazy loading would constantly re-seek backwards for prior sessions, making it slower and more complex for no meaningful memory benefit.

---

## Timestamp Storage

| Option | Description | Selected |
|--------|-------------|----------|
| Timezone-aware ET index | `datetime64[ns, America/New_York]` as DataFrame index | ✓ |
| Naive UTC + conversion | Store as UTC, convert to ET on-the-fly in each module | |

**User's choice:** Timezone-aware `datetime64[ns, America/New_York]` as the index
**Notes:** Every session boundary, overnight window, RTH open, aggressive window, and EOD cutoff is defined in ET. Storing naive UTC and converting on-the-fly means doing conversion in dozens of places; one missed conversion is a silent bug that misclassifies overnight bars as RTH. Make ET canonical at load time, once.

---

## Synthetic Bar Fill Policy

| Option | Description | Selected |
|--------|-------------|----------|
| Forward-fill all OHLCV + exclude from ATR | Complete data structure, tagged, ATR-safe | ✓ |
| Forward-fill close only | Minimal fill, only what SMT needs | |
| Leave NaN | Mark missing, handle downstream | |

**User's choice:** Forward-fill all OHLCV, exclude synthetic from ATR, skip SMT correlation windows with >2/20 synthetic bars
**Notes:** Forward-fill all five fields so nothing downstream throws missing-field errors. Tag `is_synthetic=True`. Exclude from ATR — flat synthetic bars compress ATR and make stops too tight. For SMT: skip correlation windows with more than 2 of 20 bars synthetic; isolated synthetics are fine but a run means the feed was dead.

---

## Config Design

| Option | Description | Selected |
|--------|-------------|----------|
| Hardcoded dataclass | Values in Python source, immutable | |
| YAML → frozen dataclass | YAML file loaded at startup, validated, frozen at runtime | ✓ |
| JSON config | Similar to YAML but less readable for complex nested structures | |

**User's choice:** YAML → frozen dataclass (option b)
**Notes:** Hardcoding means every tweak requires code change + re-commit + re-run. YAML gives a single editable file, version-controllable, swappable between environments. Frozen dataclass ensures immutability at runtime. Flow: load YAML → validate → instantiate frozen dataclass → pass everywhere.

---

## Module Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Create all stub files day one | Full module list with NotImplementedError signatures | ✓ |
| Only Phase 1 files | Create modules as each phase needs them | |

**User's choice:** All 18 stub files created in Phase 1
**Notes:** Valid import graph from day one, IDE autocomplete across full codebase, Phase 2+ never creates files — only fills stubs. User provided explicit canonical module list of 15 source modules. "A stub that raises NotImplementedError is infinitely better than a missing import that breaks unrelated tests."

---

## Agent's Discretion

- Resolved module structure conflicts between user's list and PROJECT.md original layout. User's list is canonical.
- `session.py` designated as owning session ID assignment, iteration, and all window boundary definitions.

## Deferred Ideas

None — discussion stayed within phase scope.
