# Phase 5: Trade Execution Engine & Reporting - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Resolve every TradeSetup against subsequent bars using a formal position state machine, implement full 60%/40% partial exit logic with exact fill prices, compute P&L for both long and short trades, generate per-trade Plotly HTML charts with SVP overlay, and write all output to `D:\Algorithms\Wicked Backtest Results` with per-trade incremental saves.

</domain>

<decisions>
## Implementation Decisions

### Position State Machine
- **D-01:** Formal state machine with explicit states: `PENDING_FILL → OPEN_FULL → OPEN_PARTIAL → CLOSED`. Each bar's update is a clean switch on current state + bar events → new state. No conditional soup.
- **D-02:** One position at a time per session. A new setup is only evaluated when the current position reaches `CLOSED`. The strategy is a precision sniper approach — multiple simultaneous positions would require capital allocation, correlated drawdown handling, and directional conflict resolution, none of which are in scope.
- **D-03:** Daily limit of 3 trades applies globally across the session and across both setup types. Counter increments when a trade transitions to `OPEN_FULL`, not at setup creation.

### Fill Price Precision
- **D-04:** Fill at exact target price for TP1 and TP2 (limit order modeling). Fill at exact SL price for stops. Bar close is irrelevant for these exits — they model limit/stop orders, not market-on-close.
- **D-05:** Conflict bar resolution (same bar hits both TP1 and SL): **TP1 wins.** Rationale: price must have traded through TP1 before reversing to hit SL. Implementation: always check TP1 before SL in bar evaluation order.
- **D-06:** After TP1 fires on a conflict bar: partial exit at TP1 price, SL moves to breakeven, then check whether the new breakeven SL was also hit on the same bar. If yes, remaining 40% exits at breakeven. This is the correct outcome — partial profits protected.
- **D-07:** Hard stop (body closes inside LVN): fills at bar close price (the only price that's meaningful since the condition is evaluated on bar close).
- **D-08:** EOD close (3:45 PM ET): fills at bar close price.

### Plotly Chart Design
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

### Incremental Save & File Structure
- **D-12:** Per-trade append: write one CSV row immediately after each trade closes. A crash mid-session loses at most the current open position's outcome, never completed trades.
- **D-13:** CSV implementation: on first write — check file existence; if not, write with headers; if exists, open in append mode without headers. Keep an in-memory list as secondary buffer for summary statistics at the end.
- **D-14:** File naming convention:
  - CSV: `backtest_results_{run_timestamp}.csv` (multiple runs don't overwrite)
  - Charts directory: `charts_{run_timestamp}/`
  - Individual charts: `{trade_index}_{date}_{direction}_{setup_type}.html`
- **D-15:** All output to `D:\Algorithms\Wicked Backtest Results\run_YYYYMMDD_HHMMSS\` (per PROJECT.md).

### Agent's Discretion
- Position state machine implementation: Python `Enum` for states, single `update(bar)` method on the `Position` class that returns a list of fill events (0, 1, or 2 fills per bar possible on conflict bars).
- SVP histogram rendering: use Plotly `go.Bar` with horizontal orientation, secondary y-axis aligned to the candlestick price axis.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Strategy Specification
- `.planning/REQUIREMENTS.md` — SL-01 through SL-04, TP-01 through TP-07, EXEC-01 through EXEC-06, REPORT-01 through REPORT-05
- `.planning/PROJECT.md` — Exit management rules, position sizing formula, output directory structure

### Architecture & Design
- `.planning/research/ARCHITECTURE.md` — RTH execution phase, output layer
- `.planning/research/PITFALLS.md` — P4 (short P&L polarity), C2 (position sizing ÷0), C3 (commission double-counting), C4 (partial exit commission under-counting), C7 (RR ÷0), C8 (profit factor infinity)

### Prior Phase Context
- `.planning/phases/01-data-infrastructure-core-candle-math/01-CONTEXT.md` — D-07/D-08 (config system with InstrumentConfig: tick_size, point_value, commission_per_side)
- `.planning/phases/03-volume-profile-lvn-single-prints/03-CONTEXT.md` — D-01–D-03 (VolumeProfile object for SVP overlay), LVN zone validity for hard stop checks
- `.planning/phases/04-signal-generation-ismt-smt-entry/04-CONTEXT.md` — D-12–D-14 (TradeSetup production, daily limit, per-LVN suppression)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Phase 1 provides: `config.py` (InstrumentConfig with point_value, commission_per_side), `session.py` (EOD cutoff time)
- Phase 3 provides: `volume_profile.py` (VolumeProfile object for chart overlay), `lvn.py` (LVN zones for hard stop body-inside check)
- Phase 4 provides: `entry.py` (TradeSetup objects as input)

### Established Patterns
- Session-scoped state cleared at boundaries (position is always flat at session end by design — EOD close)
- Numpy arrays for price computations (Phase 3 established)
- Frozen config passed by reference (Phase 1 established)

### Integration Points
- `position.py` consumes: TradeSetup from `entry.py`, bar stream from `data_loader.py`, LVN zones from `lvn.py`
- `position.py` produces: TradeResult objects consumed by `metrics.py` (Phase 6) and `plotting.py`
- `plotting.py` consumes: TradeResult, VolumeProfile (for SVP overlay), LVN zones (for shaded rectangles)
- `backtest.py` orchestrates: the full session loop calling position updates per bar

</code_context>

<specifics>
## Specific Ideas

- User specified exact conflict bar resolution: TP1 checked first → partial exit → SL moves to breakeven → check if breakeven hit on same bar → remaining exits at breakeven
- User specified exact chart context: 60 bars pre-entry, 30 bars post-exit
- User specified exact file naming: `{trade_index}_{date}_{direction}_{setup_type}.html`
- User was explicit about one-position-at-a-time: "this strategy is a precision sniper approach, not a basket trader"

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-trade-execution-engine-reporting*
*Context gathered: 2026-04-05*
