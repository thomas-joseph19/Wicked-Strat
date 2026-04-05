# Phase 6: Institutional Metrics — Technical Research

**Phase:** 06-institutional-metrics  
**Updated:** 2026-04-05 (forced `--research`)  
**Question answered:** What do we need to know to plan implementation well?

---

## 1. Requirement sources (resolved tensions)

| Source | Intent |
|--------|--------|
| `REQUIREMENTS.md` METRIC-01..06 | Baseline formulas: daily P&L, Sharpe, Sortino, max DD on equity, profit factor, win-rate stats |
| `06-CONTEXT.md` D-01..D-12 | **Authoritative for this repo:** fixed $100k daily return denominator; **include zero-trade days** in return series; compounded equity for drawdown/Calmar; Sortino with downside-only deviation; profit factor = `gross_wins` when no losers (C8); 9-section `summary.md` + `summary.json` |
| `ROADMAP.md` success criteria | Concrete examples (two trades → daily P&L, rolling peak drawdown, PF guard, sqrt(252)) |

**Sharpe (locked):** \( \text{Sharpe} = (\mu_{\text{daily}} / \sigma_{\text{daily}}) \times \sqrt{252} \) with \(\mu, \sigma\) over **all** days in the daily return series (including 0-return days). Risk-free = 0 per D-05 → “excess” = raw daily return.

**Sortino (locked to CONTEXT D-07):** Use **downside returns only** \(r < 0\) for downside deviation. Standard implementation:

- `downside_squared_mean = mean(r**2 for r in daily_returns if r < 0)` (if empty → document Sortino as `inf` or `None` and flag in Section 2 table).
- `downside_deviation_daily = sqrt(downside_squared_mean)` then annualize: `downside_dev_annual = downside_deviation_daily * sqrt(252)`.
- `sortino = (mean_daily_return * 252) / downside_dev_annual` when denominator > 0.

*(If `mean_daily_return * 252` vs `mean * sqrt(252)` conflicts with METRIC-03 wording, implement the CONTEXT formula and cite D-07 in module docstring.)*

**Max drawdown (P8 / METRIC-04 / D-09):** Build **compounded** equity \(E_0 = 100{,}000\), \(E_t = E_{t-1}(1 + r_t)\). Then `running_peak = cummax(E)`, `drawdown_t = (E_t - running_peak_t) / running_peak_t`. Report `min(drawdown_t)` (negative fraction) and dollars.

**Daily return denominator (D-01):** Always `account_size` from config (default 100_000), not rolling equity.

**Zero-trade days (D-03):** The backtest orchestrator must supply a **complete ordered date index** for the run (every calendar trading day in range, or every session date present in the merged bar calendar—**planner locks:** use **session dates that appear in the bar feed for the run**, union with dates that have trades, sorted; for true calendar completeness Phase 7 audit may tighten). Minimum for Phase 6: for any **session_date** in the union of `{trade.session_date}`, emit a row; **plus** optional parameter `all_session_dates: Sequence[str]` to inject zero-PnL days for Sharpe integrity.

---

## 2. Inputs and data contracts

- **Primary input:** `list[TradeResult]` from `position.build_trade_result` / backtest collector (`session_date: str` ISO, `net_pnl: float`, `exit_type`, `setup_type`, `signal_source`, bar indices optional for metrics).
- **Config:** `StrategyThresholds.account_size` (or `AppConfig`) for denominator and Section 8 YAML dump (reuse `load_config` / existing YAML path).
- **Session diagnostics (Section 7):** Not yet produced by minimal `run_session_backtest`. Phase 6 should define `SessionDiagnostics` dataclass (counts, skipped NEUTRAL, etc.) with **stub zeros** from current backtest and a **hook** for Phase 7 full harness to populate.

---

## 3. Module layout (recommendation)

| Module | Responsibility |
|--------|----------------|
| `src/metrics/` package **or** single `src/metrics.py` | Prefer **single `metrics.py`** first (~400 line budget); split if exceeded |
| `src/metrics.py` | Pure functions: `daily_pnl_series`, `compounded_equity`, `max_drawdown_stats`, `sharpe_ratio`, `sortino_ratio`, `calmar_ratio`, `profit_factor`, `trade_statistics`, `annual_breakdown` |
| `src/summary_builder.py` *(optional)* | 9-section markdown + JSON from computed structs; or nested in `metrics.py` |

**Testing:** `tests/phase06/` mirror phase05 style; use synthetic `TradeResult` lists (no parquet in unit tests).

---

## 4. summary.md / summary.json

- **Replace** Phase 5 stub content when metrics run completes (or write `summary.md` next to run root per `RunPaths.run_root`—align with `RunWriter.finalize_summary`: either **extend** `RunWriter` with `write_full_metrics_summary` or **deprecate** stub and call new finalizer from `backtest.py` after all trades).
- **summary.json:** `dataclasses.asdict` or explicit JSON-serializable nested dict mirroring tables.

---

## 5. Edge cases (from PITFALLS)

- **C8:** `sum(negative_pnls) == 0` → `profit_factor = gross_wins` (finite).
- **P8:** Never drawdown vs fixed $100k only; always vs rolling peak of compounded equity.
- **Std dev zero:** Sharpe undefined → document as `None` or `0.0` with warning bullet in Section 9.

---

## 6. Integration touchpoints

- `src/backtest.py`: after session loop, call `compute_run_metrics(trades, paths, config, session_diag=...)` once.
- `src/reporting.py`: optional new method `write_institutional_summary(...)` or extend `finalize_summary` behind flag to avoid breaking Phase 5 tests—**planner should specify backward compatibility** (Phase 5 tests expect stub header; either version bump string or separate filename `summary_institutional.md`—**recommend:** single `summary.md` replaced when metrics module runs; update Phase 5 test to accept “Phase 5 stub **or** Phase 6 header” OR move stub test to only mock writer without full pipeline).

---

## Validation Architecture

Phase 6 validation is **pytest-first, pure-function heavy**:

| Dimension | Approach |
|-----------|----------|
| Correctness | Golden-value tests for daily agg, drawdown ladder (two-peak equity), Sharpe/Sortino on fixed arrays |
| Regression | METRIC-01..06 traceability table in `06-VALIDATION.md` |
| Integration | One `tmp_path` test: metrics + write `summary.json` keys present |
| Manual | Human reads sample `summary.md` once for narrative quality (not CI-gated) |

---

## RESEARCH COMPLETE

Ready for `gsd-planner` / PLAN.md authoring with `06-CONTEXT.md` as decision authority where it extends REQUIREMENTS.md.
