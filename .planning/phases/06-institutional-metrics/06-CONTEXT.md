# Phase 6: Institutional Metrics - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Aggregate trade results to daily P&L, compute all risk-adjusted performance metrics (Sharpe, Sortino, Calmar, Max Drawdown, Profit Factor, Recovery Factor), build the compounded equity curve, produce a comprehensive 9-section summary.md with narrative and tables, and compile session/setup quality diagnostics.

</domain>

<decisions>
## Implementation Decisions

### Daily Return Denominator
- **D-01:** Fixed starting capital ($100k) as denominator for ALL daily return calculations. Rolling denominator creates asymmetric distortion (smaller returns during drawdowns, larger during winning streaks) that corrupts Sharpe/Sortino/CAGR year-over-year comparisons. Institutional practice for strategy backtests.
- **D-02:** Daily return = `net_daily_pnl / 100000`. Net means after commissions.
- **D-03:** Days with zero trades get daily return of exactly 0.0 — do NOT skip or interpolate. Zero-return days must appear in the daily return series because they affect the Sharpe denominator (excluding them inflates Sharpe by artificially reducing measured volatility). This is one of the most common backtest reporting errors.
- **D-04:** A compounded equity curve is computed as a secondary output: `equity[i] = equity[i-1] * (1 + daily_return[i])` starting from $100k. Used for max drawdown and Calmar — path-dependent metrics that need actual capital at risk.

### Risk-Free Rate
- **D-05:** Zero risk-free rate for all years across the full 12-year window. Static, fixed. Measures the strategy's raw edge in isolation, not relative to a capital deployment alternative.
- **D-06:** Sharpe = `(mean_daily_return / std_daily_return) * sqrt(252)`. Both mean and std computed over ALL calendar trading days including zero-return days. 252 annualization factor (US futures standard — not 365, not 261).
- **D-07:** Sortino formula:
  ```
  downside_returns   = [r for r in daily_returns if r < 0]
  downside_deviation = sqrt(mean(r**2 for r in downside_returns)) * sqrt(252)
  sortino            = (mean_daily_return * 252) / downside_deviation
  ```
  If `downside_returns` is empty (all days profitable or flat): set Sortino to `inf` and flag explicitly in the report.
- **D-08:** Calmar = `annualized_return / abs(max_drawdown_pct)`. Uses the compounded equity curve. `annualized_return = (1 + total_return)^(1/num_years) - 1`.

### Max Drawdown Calculation
- **D-09:** Compute on the running compounded equity curve, NOT on the daily return series directly. `max_drawdown = max((peak - trough) / peak)` using the standard running-maximum method.
- **D-10:** Drawdown duration measured in **calendar days** (not trading days) between peak date and recovery date (first day equity exceeds prior peak). Calendar days is the convention because that's what it feels like to live through a drawdown.

### Summary.md Structure — 9 Sections
- **D-11:** Narrative report with sections, each containing a brief interpretive sentence followed by a dense data table. The exact template is specified below:

**Section 1 — Executive Summary:** One paragraph (3–5 sentences) stating total net P&L, annualized return, Sharpe, max drawdown, win rate. Written as a human would write it.

**Section 2 — Risk-Adjusted Performance:** Table with Total Net P&L, Total Return, CAGR, Sharpe (ann.), Sortino (ann.), Calmar, Max DD ($), Max DD (%), Max DD Duration, Recovery Factor, Profit Factor.

**Section 3 — Trade Statistics:** Table with Total Trades, Win/Loss/Scratch counts (with percentages), Avg Win/Loss, Largest Win/Loss, Avg RR, Avg Bars Held (winners vs losers), TP1/TP2 Hit Rate, Hard Stop Rate, per-setup-type win rates (3-Step, Aggressive Ledge), per-signal-type win rates (ISMT, SMT). Scratch trades (breakeven SL after TP1 partial) tracked separately — they are partial wins, not losses.

**Section 4 — Daily P&L Distribution:** Table with Trading Days, Days With Trades (%), Profitable/Losing Days, Zero-Trade Days, Best/Worst Day, Avg Daily P&L, Std Dev, Skewness, Kurtosis. Skew and kurtosis matter for tail analysis.

**Section 5 — Annual Breakdown:** Table with Year | Trades | Win% | Net P&L | Return | Sharpe | Max DD columns. Per-year Sharpe uses that year's daily returns only, annualized by sqrt(252). Includes an ALL row for aggregate. This is the primary consistency check.

**Section 6 — Drawdown Analysis:** Table listing all drawdowns exceeding 5% of initial capital, sorted by depth descending, capped at 10 rows. Columns: Peak Date, Trough Date, Recovery Date, Depth ($), Depth (%), Duration (calendar days). Below table: one sentence noting if worst drawdown coincided with a known market event — requires a small hardcoded lookup table of `{date_range: event_name}` for the 12-year window (COVID crash, 2022 rate hike cycle, etc.).

**Section 7 — Session & Setup Quality:** Table with Total Sessions Analyzed, Sessions With Valid Bias (%), Sessions Skipped (NEUTRAL), Avg Active LVNs/Session, Avg LVNs Invalidated/Session, Avg SP Zones/Session, SP Zones Respected Overnight (%), Setups Generated, Setups Rejected (RR < 1.5), Setups Rejected (SL bounds), Setups Taken. Interpretive note explaining what low/high values mean diagnostically.

**Section 8 — Parameter Snapshot:** Full config YAML contents pasted verbatim in a code block. Ensures the summary is self-contained and reproducible.

**Section 9 — Notes & Warnings:** Auto-generated bulleted list: sessions skipped due to data gaps > 30 min, days where max daily trade limit hit, sessions with zero surviving LVNs, years with < 50 trading days (flag for Sharpe exclusion), synthetic bar rate per instrument (flag if > 2%).

### Profit Factor Guard
- **D-12:** If zero losing trades: `profit_factor = gross_wins` (not `inf` or error). Per pitfall C8.

### Agent's Discretion
- Recovery Factor = `total_net_pnl / abs(max_drawdown_dollars)`.
- Known market event lookup table: hardcoded dict with entries like `("2020-02-19", "2020-03-23"): "COVID-19 Crash"`, `("2022-01-03", "2022-10-13"): "2022 Rate Hike Cycle"`, etc.
- summary.json machine-readable output mirrors all summary.md tables as nested dicts.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Strategy Specification
- `.planning/REQUIREMENTS.md` — METRIC-01 through METRIC-06
- `.planning/PROJECT.md` — Output directory structure (summary.md location)

### Architecture & Design
- `.planning/research/PITFALLS.md` — P8 (drawdown from fixed base — resolved: use rolling peak on compounded curve), C8 (profit factor infinity guard)

### Prior Phase Context
- `.planning/phases/01-data-infrastructure-core-candle-math/01-CONTEXT.md` — D-07/D-08 (config system — YAML contents for Section 8)
- `.planning/phases/05-trade-execution-engine-reporting/05-CONTEXT.md` — D-01 (TradeResult objects as input), D-12–D-15 (output file structure)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Phase 5 provides: `position.py` (TradeResult objects with net_pnl, exit_type, setup_type, signal_source)
- Phase 1 provides: `config.py` (account_size, full YAML contents for Section 8 parameter snapshot)

### Established Patterns
- Numpy arrays for numerical computations
- Per-trade append CSV from Phase 5 (metrics reads from TradeResult list, not CSV)

### Integration Points
- `metrics.py` consumes: list of TradeResult objects from `backtest.py` orchestrator
- `metrics.py` produces: summary.md, summary.json, compounded equity curve
- `backtest.py` collects session-level diagnostics (LVN counts, bias stats, etc.) for Section 7

</code_context>

<specifics>
## Specific Ideas

- User provided the complete 9-section summary.md template with exact table schemas
- User specified exact Sharpe/Sortino/Calmar formulas with correct annualization
- User was explicit: zero-return days MUST be included in Sharpe calculation
- User was explicit: drawdown duration in calendar days, not trading days
- User was explicit: scratch trades (breakeven after TP1) are partial wins, not losses
- User specified known market event lookup table for drawdown analysis narrative

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 06-institutional-metrics*
*Context gathered: 2026-04-05*
