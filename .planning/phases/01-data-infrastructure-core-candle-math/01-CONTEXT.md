# Phase 1: Data Infrastructure & Core Candle Math - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Load both parquet datasets (ES + NQ), normalize to a unified schema, implement session boundary logic (24h Globex, 6 PM ET), build a synchronized dual-instrument bar stream with synthetic bar handling, provide foundational candle math (ATR), define the strategy configuration system, and establish the full module structure with stubs for all downstream phases.

</domain>

<decisions>
## Implementation Decisions

### Data Loading Strategy
- **D-01:** Eager loading — load both parquet files fully into RAM at startup. Both files total ~157MB on disk; at float32 this fits comfortably (~300MB working set). Build the session index once and keep it in memory for the entire run. Rationale: the strategy needs random access across full history for multi-session LVN confluence lookups and MC chunk sampling; lazy/chunked loading would constantly re-seek backwards for prior sessions.

### Timestamp & Timezone Handling
- **D-02:** Store timestamps as timezone-aware `datetime64[ns, America/New_York]` as the DataFrame index. ET is the canonical representation — all session boundaries, overnight windows, RTH opens, aggressive windows, and EOD cutoffs are defined in ET. Convert at load time, once, and never convert again downstream. This eliminates an entire class of silent bugs (misclassifying overnight bars as RTH).
- **D-03:** DST handled via `zoneinfo.ZoneInfo("America/New_York")` — no hardcoded UTC offsets anywhere in the codebase.

### Synthetic Bar Fill Policy
- **D-04:** Forward-fill ALL five OHLCV fields for missing bars so the data structure is always complete — nothing downstream throws a missing-field error. Tag synthetic bars with `is_synthetic=True`.
- **D-05:** Exclude synthetic bars from ATR calculation entirely — a flat synthetic bar with zero real volume would artificially compress ATR, making stop losses too tight.
- **D-06:** For SMT correlation windows: skip any 20-bar correlation window where more than 2 of the 20 bars are synthetic. One or two isolated synthetic bars are fine; a run of them means the feed was dead and correlation is meaningless.

### Configuration System
- **D-07:** YAML config file loaded at startup → frozen Python dataclass for runtime. The YAML file is editable, version-controllable, and swappable between environments without touching source code. The frozen dataclass ensures parameters are immutable during a run. Flow: load YAML once → validate all fields → instantiate frozen dataclass → pass everywhere by reference.
- **D-08:** Two config dataclasses: `InstrumentConfig` (tick_size, point_value, commission_per_side) and `StrategyThresholds` (all tunable parameters from the specification).

### Module Structure
- **D-09:** Create all module files in Phase 1 with function/class signatures and `NotImplementedError` stubs. This makes the import graph valid immediately, enables IDE autocomplete across the full codebase, and ensures Phase 2+ only fills in stubs — never creates new files.
- **D-10:** Canonical module list (under `src/`):

| Module | Responsibility |
|--------|---------------|
| `data_loader.py` | Parquet loading, column normalization, synchronized NQ+ES stream |
| `session.py` | Session ID assignment, session iteration, window definitions (pre-market, RTH, overnight, aggressive) |
| `core.py` | ATR_5, ATR_20, candle math — pure functions, no state |
| `config.py` | YAML loading, field validation, `InstrumentConfig` + `StrategyThresholds` frozen dataclasses |
| `volume_profile.py` | SVP construction, POC, VAH, VAL |
| `lvn.py` | LVN detection, all 4 filters, real-time invalidation |
| `single_prints.py` | SP detection, zone grouping, overnight respect check |
| `tpo.py` | TPO bias calculation (30-min bars) |
| `swings.py` | Swing high/low detection, confirmation delay, registry |
| `ismt.py` | ISMT detection (single-instrument NQ) |
| `smt.py` | SMT detection (dual-instrument NQ+ES), correlation tracking |
| `entry.py` | 3-Step Model + Aggressive Ledge entry logic, `get_structural_confirmation()` |
| `position.py` | TradeSetup, TradeResult, bar-by-bar position management, partial exits |
| `metrics.py` | Sharpe, Sortino, Max Drawdown, Profit Factor, win rate |
| `plotting.py` | Per-trade Plotly HTML candlestick charts |
| `backtest.py` | Main session loop orchestrator |
| `utils.py` | Shared utilities |
| `ml_pipeline.py` | M2 stub only — feature engineering, walk-forward, MC engine |

### Agent's Discretion
- Module boundaries: the agent resolved the user's module list against PROJECT.md's original structure. Key changes from original: `liquidity.py` → split into `lvn.py` + (logic stays in `volume_profile.py`); `signal.py` → renamed to `entry.py`; `execution.py` → renamed to `position.py`; added `session.py`, `config.py`, `backtest.py`, `utils.py`. The user's list is canonical going forward.
- `session.py` owns: session ID assignment, session-by-session iteration (groupby), and all window boundary definitions (pre-market cutoff, RTH open, aggressive window, EOD).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Strategy Specification
- `.planning/PROJECT.md` — Full strategy rules, data schema, output directory, key decisions
- `.planning/REQUIREMENTS.md` — All DATA-*, CORE-* requirements with acceptance criteria

### Architecture & Design
- `.planning/research/ARCHITECTURE.md` — Component boundaries, data flow, session architecture, dual-instrument sync, anti-patterns
- `.planning/research/STACK.md` — Technology stack decisions (pandas, numpy, zoneinfo, pyarrow)

### Known Pitfalls
- `.planning/research/PITFALLS.md` — P6 (resample label lookahead), C1 (DST), PERF1 (dict vs array lookups), PERF2 (memory at scale) are directly relevant to Phase 1

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — this is Phase 1 of a greenfield project. No existing source code.

### Established Patterns
- None yet — Phase 1 establishes the patterns all subsequent phases will follow.

### Integration Points
- Two parquet files in project root: `1Min_ES.parquet` (58MB), `nq_1min_10y.parquet` (99MB)
- Output directory: `D:\Algorithms\Wicked Backtest Results\run_YYYYMMDD_HHMMSS\`
- CLI entry point: `main.py` in project root

</code_context>

<specifics>
## Specific Ideas

- User explicitly wants the frozen dataclass pattern: "load YAML once at startup, validate all fields, instantiate the frozen dataclass, and pass it everywhere"
- User explicitly wants `NotImplementedError` stubs: "A stub that raises NotImplementedError is infinitely better than a missing import that breaks unrelated tests"
- The user's expanded module list (15 modules) supersedes the original PROJECT.md structure (10 modules)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-data-infrastructure-core-candle-math*
*Context gathered: 2026-04-05*
