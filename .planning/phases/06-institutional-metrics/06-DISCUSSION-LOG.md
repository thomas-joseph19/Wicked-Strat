# Phase 6: Institutional Metrics - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-05
**Phase:** 06-institutional-metrics
**Areas discussed:** Daily return denominator, Risk-free rate, Summary.md structure

---

## Daily Return Denominator

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed starting capital ($100k) | Simple, institutional standard, no compounding distortion | ✓ |
| Rolling account balance | Returns shrink during drawdowns, grow during streaks | |

**User's choice:** Fixed $100k for all return calculations
**Notes:** Rolling denominator creates asymmetric distortion in Sharpe/Sortino/CAGR. Compounded equity curve is a secondary output for drawdown/Calmar only. Zero-trade days MUST appear with 0.0 return — excluding them inflates Sharpe by reducing measured volatility. "This is one of the most common backtest reporting errors."

---

## Risk-Free Rate

| Option | Description | Selected |
|--------|-------------|----------|
| Zero, static | Measures raw strategy edge in isolation | ✓ |
| Treasury rate (time-varying) | Adjusts for risk-free alternative | |
| Fixed constant (e.g., 2%) | Simple but arbitrary | |

**User's choice:** Zero for all years
**Notes:** Measuring strategy's raw edge, not comparing against cash deployment. Time-varying Treasury introduces macro factor unrelated to LVN detection logic. Sharpe = `(mean/std) * sqrt(252)`. Sortino uses downside deviation only. Calmar uses compounded equity curve. 252 annualization (US futures standard).

---

## Summary.md Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Narrative + tables (9 sections) | Sections with interpretive sentence + dense table | ✓ |
| Dense tables only | No narrative context | |
| Narrative only | No structured tables | |

**User's choice:** 9-section narrative report with tables
**Notes:** User provided complete template with exact table schemas for all 9 sections: (1) Executive Summary, (2) Risk-Adjusted Performance, (3) Trade Statistics, (4) Daily P&L Distribution, (5) Annual Breakdown, (6) Drawdown Analysis with known market events, (7) Session & Setup Quality diagnostics, (8) Parameter Snapshot (full config YAML), (9) Notes & Warnings (auto-generated). Scratch trades tracked separately as partial wins. Drawdown table capped at 10 rows, 5% threshold, sorted by depth.

---

## Agent's Discretion

- Recovery Factor formula: total_net_pnl / abs(max_drawdown_dollars)
- Known market event lookup table hardcoded
- summary.json mirrors summary.md as nested dicts

## Deferred Ideas

None — discussion stayed within phase scope.
