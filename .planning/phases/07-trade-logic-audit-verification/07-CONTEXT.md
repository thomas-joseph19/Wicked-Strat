# Phase 7: Trade Logic Audit & Verification - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Run the full audit checklist from the specification, pass the reproducibility gate (2 identical runs = identical trades.csv), auto-generate an audit_report.md, fix any remaining bugs, add an equity curve chart and enhanced dual-instrument per-trade charts, and designate M1 complete.

</domain>

<decisions>
## Implementation Decisions

### Audit Execution Mode
- **D-01:** Manual execution. Run the full backtest twice manually from the CLI with the same parameters and compare the two `trades.csv` files for byte-identical match. No automated audit orchestration script — the developer runs the two backtest commands and performs the diff.
- **D-02:** The comparison itself can be a simple script or shell command (`diff` / `fc`) — but the two backtest runs are triggered manually, not from within an audit tool.

### Edge Case Test Design
- **D-03:** Agent's discretion on test structure. Permanent pytest unit tests for the critical edge cases (AUDIT-02: entry == stop skip, AUDIT-03: short polarity, AUDIT-06: commission counting). These run on every `pytest` invocation as regression guards. Constructed/synthetic trade data for each test — not dependent on real market data.

### Audit Report
- **D-04:** Auto-generated `audit_report.md` produced by a script that runs all checklist items programmatically and writes pass/fail results with timestamps and exact values checked. Each AUDIT-01 through AUDIT-07 item gets a row with: item ID, description, result (PASS/FAIL), evidence (the actual value or comparison output), timestamp.

### Equity Curve Chart (Cross-Phase: Expands Phase 6 Output)
- **D-05:** Produce a standalone Plotly HTML chart of the compounded equity curve across the full backtest window. X-axis: date. Y-axis: equity ($). Include:
  - Equity line (primary)
  - Drawdown shading (filled area between equity and running peak, colored red with low opacity)
  - Horizontal line at $100k starting capital
  - Annotations for the top 3 deepest drawdowns (peak date → trough date labels)
- **D-06:** Save as `equity_curve_{run_timestamp}.html` in the run output directory alongside the CSV and charts folder.

### Enhanced Per-Trade Charts (Cross-Phase: Expands Phase 5 Chart Spec)
- **D-07:** Per-trade charts show BOTH NQ and ES in a dual-panel layout:
  - **Top panel:** NQ candlestick chart (primary trading instrument) with all existing overlays from Phase 5 D-10 (entry, SL, TP1, TP2, LVN zone, SVP histogram, fill markers)
  - **Bottom panel:** ES candlestick chart for the same time window, showing the ES price action that was consumed for SMT/ISMT confluence
- **D-08:** Confluence annotations on the NQ panel:
  - If ISMT-confirmed: mark the SH1/SH2 (bearish) or SL1/SL2 (bullish) swing points with labeled markers, draw a horizontal line at the sweep level, and annotate `confirmed_at` bar
  - If SMT-confirmed: draw vertical dashed lines at the NQ swing and ES swing bars, label the divergence (e.g., "NQ HH / ES LH"), annotate correlation value
  - TPO bias label in top-left corner of NQ panel: "BIAS: BULLISH" or "BIAS: BEARISH" with the upper_ratio percentage
  - SP zones used as targets: shaded green rectangles (similar to LVN yellow shading)
- **D-09:** Same time window for both panels (60 bars pre-entry, 30 bars post-exit from Phase 5 D-09) so NQ and ES are perfectly time-aligned for visual divergence comparison.

### Agent's Discretion
- Pytest fixtures for synthetic trade data: use `@pytest.fixture` with known prices that produce deterministic P&L outcomes.
- Audit report script location: `src/audit.py` or `tests/audit.py` — agent decides based on what makes the import graph cleanest.
- Plotly subplot layout for dual-panel charts: `make_subplots(rows=2, cols=1, shared_xaxes=True)` with NQ on top (70% height), ES on bottom (30% height).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Strategy Specification
- `.planning/REQUIREMENTS.md` — AUDIT-01 through AUDIT-07
- `.planning/PROJECT.md` — Audit checklist items, reproducibility gate definition

### Architecture & Design
- `.planning/research/PITFALLS.md` — ALL pitfalls (P1–P8, C1–C8) — Phase 7 validates that every one was handled correctly

### Prior Phase Context (ALL phases relevant — this phase validates the entire M1 chain)
- `.planning/phases/01-data-infrastructure-core-candle-math/01-CONTEXT.md` — D-02 (ET timestamps), D-04–D-06 (synthetic bars)
- `.planning/phases/02-swing-detection-tpo-bias-engine/02-CONTEXT.md` — D-01–D-03 (swing registry), D-06–D-08 (30-min aggregation)
- `.planning/phases/03-volume-profile-lvn-single-prints/03-CONTEXT.md` — D-01–D-03 (numpy VP), D-10–D-12 (SP timing)
- `.planning/phases/04-signal-generation-ismt-smt-entry/04-CONTEXT.md` — D-01–D-03 (ISMT confirmation), D-04 (SMT > ISMT override), D-08–D-11 (approach definition)
- `.planning/phases/05-trade-execution-engine-reporting/05-CONTEXT.md` — D-01–D-03 (state machine), D-04–D-08 (fill precision), D-09–D-11 (chart spec — now expanded by D-07–D-09)
- `.planning/phases/06-institutional-metrics/06-CONTEXT.md` — D-01–D-04 (daily returns), D-06–D-08 (Sharpe/Sortino/Calmar formulas), D-09–D-10 (drawdown), D-11 (summary.md template — now expanded with equity curve)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- All Phase 1–6 modules are the system under test
- `plotting.py` (Phase 5) chart generation — expanded here to include dual-panel and confluences
- `metrics.py` (Phase 6) equity curve computation — used as input for equity curve chart

### Established Patterns
- Plotly HTML charts (Phase 5 established)
- Per-trade incremental save (Phase 5 established)
- Numpy arrays for price-indexed data (Phase 3 established)

### Integration Points
- Audit script imports all `src/` modules for programmatic testing
- Equity curve chart consumes the compounded equity curve from `metrics.py`
- Enhanced per-trade charts require: TradeResult + VolumeProfile + LVN zones + ISMT/SMT signal details + TPO bias + SP zones + ES bar data — the chart function needs access to all confluences used in the entry decision

</code_context>

<specifics>
## Specific Ideas

- User wants both NQ AND ES visible on per-trade charts — critical for visually verifying SMT divergence
- User wants confluence annotations (ISMT swing markers, SMT divergence labels, TPO bias, SP target zones) — these make the charts self-documenting for visual review
- User specified equity curve with drawdown shading and top-3 drawdown annotations

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 07-trade-logic-audit-verification*
*Context gathered: 2026-04-05*
