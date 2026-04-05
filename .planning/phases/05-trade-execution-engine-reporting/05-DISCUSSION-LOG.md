# Phase 5: Trade Execution Engine & Reporting - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-05
**Phase:** 05-trade-execution-engine-reporting
**Areas discussed:** Position state machine, Fill price precision, Plotly chart scope, Incremental save granularity

---

## Position State Machine

| Option | Description | Selected |
|--------|-------------|----------|
| Formal state machine | Explicit states with clean transitions | ✓ |
| Conditional checks | if/elif per bar, no formal states | |

**User's choice:** Formal states: PENDING_FILL → OPEN_FULL → OPEN_PARTIAL → CLOSED
**Notes:** "Conditional soup gets unreadable fast when you're handling hard stops, TP1 partial exits, breakeven moves, and EOD closes all in the same bar loop." One position at a time — "this strategy is a precision sniper approach, not a basket trader." New setup evaluated only when current position is CLOSED.

---

## Fill Price Precision

| Option | Description | Selected |
|--------|-------------|----------|
| Exact target/stop prices | TP1/TP2 at target, SL at stop, bar close irrelevant | ✓ |
| Bar close for all exits | Model as market-on-close | |

**User's choice:** Exact prices, TP1 wins on conflict bars
**Notes:** Models limit/stop orders realistically. Conflict bar (TP1 + SL same bar): check TP1 first → partial exit → SL moves to breakeven → check if breakeven hit same bar → remaining exits at breakeven. Hard stop and EOD close use bar close price (condition is bar-close-evaluated).

---

## Plotly Chart Scope

| Option | Description | Selected |
|--------|-------------|----------|
| 60 bars pre / 30 bars post + SVP overlay | Full context with volume profile | ✓ |
| Trade duration only | Minimal chart | |
| Full session | Potentially hundreds of candles | |

**User's choice:** 60/30 bar window with SVP histogram + LVN zone overlay
**Notes:** Includes entry (blue), SL (red), TP1 (green dashed), TP2 (green solid) horizontal lines. LVN zone as yellow shaded rectangle. SVP as horizontal histogram on right side. Fill events as vertical dashed lines. Title: `{instrument} | {date} | {direction} | {setup_type} | PnL: ${realized}`.

---

## Incremental Save Granularity

| Option | Description | Selected |
|--------|-------------|----------|
| Per-trade append | One CSV row after each trade closes | ✓ |
| Per-session append | Batch write after session completes | |
| Per-year append | Batch write after year completes | |

**User's choice:** Per-trade append with header-once logic
**Notes:** Crash loses at most current open position. Check file existence on first write; append mode thereafter. In-memory list as secondary buffer for end-of-run summary. File naming: `backtest_results_{run_timestamp}.csv`, charts in `charts_{run_timestamp}/`, individual: `{trade_index}_{date}_{direction}_{setup_type}.html`.

---

## Agent's Discretion

- Position state machine: Python Enum for states, single `update(bar)` method returning fill events
- SVP histogram: Plotly `go.Bar` horizontal orientation, secondary y-axis

## Deferred Ideas

None — discussion stayed within phase scope.
