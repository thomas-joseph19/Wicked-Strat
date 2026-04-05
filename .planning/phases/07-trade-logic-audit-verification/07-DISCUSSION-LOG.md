# Phase 7: Trade Logic Audit & Verification - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-05
**Phase:** 07-trade-logic-audit-verification
**Areas discussed:** Audit execution mode, Edge case tests, Audit report format, Equity curve chart, Enhanced per-trade charts

---

## Audit Execution Mode

| Option | Description | Selected |
|--------|-------------|----------|
| Manual runs + diff | Developer runs backtest twice, compares CSV | ✓ |
| Automated audit script | Script triggers two runs and compares | |
| Pytest integration | Reproducibility as a test case | |

**User's choice:** Run manually
**Notes:** Two manual backtest runs from CLI with same parameters, then diff/fc the CSV files.

---

## Edge Case Test Design

| Option | Description | Selected |
|--------|-------------|----------|
| Agent's discretion | Agent decides permanent pytest vs one-time scripts | ✓ |

**User's choice:** "Do whatever you feel is best"
**Notes:** Agent chose permanent pytest unit tests with synthetic data as regression guards.

---

## Audit Report Format

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-generated | Script runs checks, writes pass/fail with evidence | ✓ |
| Manual template | Fill in by hand | |

**User's choice:** Auto-generate
**Notes:** Each AUDIT item gets: ID, description, PASS/FAIL, evidence (actual value/comparison), timestamp.

---

## Equity Curve Chart (Added by User)

**User's request:** Produce equity curve chart as standalone Plotly HTML.
**Decision:** Compounded equity line + drawdown shading (red fill between equity and running peak) + $100k baseline + top-3 drawdown annotations. Saved as `equity_curve_{run_timestamp}.html`.

---

## Enhanced Per-Trade Charts (Added by User)

**User's request:** Per-trade charts showing BOTH NQ and ES at trade time with all confluences.
**Decision:** Dual-panel layout (NQ top 70%, ES bottom 30%, shared x-axis). NQ panel gets all existing overlays plus: ISMT swing markers, SMT divergence labels with correlation, TPO bias label, SP target zones (green shading). ES panel shows candlesticks for visual divergence comparison. Same 60/30 bar time window, perfectly aligned.

---

## Agent's Discretion

- Pytest fixtures with `@pytest.fixture` for synthetic trade data
- Audit script location: agent decides
- Dual-panel: `make_subplots(rows=2, cols=1, shared_xaxes=True)`

## Deferred Ideas

None — discussion stayed within phase scope.
