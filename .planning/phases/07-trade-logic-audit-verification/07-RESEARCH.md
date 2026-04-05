# Phase 7: Trade Logic Audit & Verification — Research

**Phase:** 07-trade-logic-audit-verification  
**Updated:** 2026-04-05 (`--research` forced)  
**Question:** What must be true to plan and execute the audit phase well?

---

## 1. Requirement mapping (AUDIT-01..07)

| ID | Intent | Automation vs manual (07-CONTEXT) |
|----|--------|-----------------------------------|
| **AUDIT-01** | Two full backtests, byte-identical trade log | **D-01/D-02:** runs triggered **manually** by developer; diff is `fc`/`diff` on files. **Executor:** document exact CLI + paths in `audit_report.md`; optional **CI skip** if parquet absent. |
| **AUDIT-02** | `entry == stop` → skip, no crash | **Pytest** on `validate_pre_entry` / setup builder / orchestrator guard — single permanent test. |
| **AUDIT-03** | Short P&L polarity | **Pytest** synthetic `TradeResult` or `Position` path (may extend `tests/phase05`). |
| **AUDIT-04** | Drawdown uses rolling peak | **Pytest** asserting `metrics.max_drawdown_stats` / equity cummax (may alias `tests/phase06` + one cross-reference in `tests/phase07`). |
| **AUDIT-05** | TPO 30m `label='left', closed='left'` | **Pytest** on known synthetic minute bars → expected bucket boundaries (see `src/tpo.py`). |
| **AUDIT-06** | Commission event counts (3 vs 2) | **Pytest** fill lists from `Position` (TP1+TP2 vs stop-only). |
| **AUDIT-07** | Exits at exact limit/stop prices | **Pytest** assert fill prices equal setup levels (existing machine tests + explicit AUDIT-07 named test). |

---

## 2. Artifact naming (trades.csv vs Phase 5 CSV)

- **REQUIREMENTS / ROADMAP** say `trades.csv`.
- **Phase 5 D-14** implements `backtest_results_{run_timestamp}.csv` under `RunPaths.csv_path`.
- **Resolution for Phase 7:** Treat **`RunPaths.csv_path`** (or configurable `trade_log_path`) as the **canonical trade log** for AUDIT-01 diffs. Optionally add **`trades.csv`** as **copy or symlink** for spec literal — **planner locks** in PLAN-01 which file is authoritative and ensure `audit_report.md` states it.

---

## 3. Audit report generator (D-04)

- Single module **`src/audit.py`** (preferred import path for `python -m` or CLI entry) exposing:
  - `run_programmatic_checks() -> list[AuditRow]`
  - `write_audit_report(path, rows, manual_instructions_md: str)`
- Rows: `AUDIT-01`..`AUDIT-07`, PASS/FAIL/SKIP/MANUAL, evidence string, ISO timestamp.
- **AUDIT-01** default row: **MANUAL** with embedded instructions referencing `main.py` / future full harness command.

---

## 4. Equity curve chart (D-05/D-06)

- Input: `pd.Series` or DataFrame of **date → equity** from `metrics.compounded_equity_from_returns` + daily table.
- Output: **`equity_curve_{run_timestamp}.html`** next to `RunPaths.run_root` (same folder as `summary.md` or `charts_{ts}/` — **planner locks**; recommend **run root** for discoverability).
- Plotly: primary line, `fill='tonexty'` or secondary trace for drawdown band vs peak, `$100k` hline, annotations for top 3 episodes from `metrics.list_drawdown_episodes`.

---

## 5. Dual-instrument + confluence charts (D-07–D-09)

- **Gap:** `build_trade_chart` today: NQ-only + SVP; ES columns exist in `bars_df` (`*_es`) but no ES panel.
- **Approach:** New function **`build_trade_chart_dual(...)`** (or extend with `mode=`) in `src/plotting.py`:
  - `make_subplots(rows=2, cols=2)` or `rows=2, cols=1` with shared x — **D-09 discretion:** NQ row wider; ES row 30% height per CONTEXT.
  - Optional **`TradeChartContext`** dataclass: `bias_label`, `upper_ratio`, `sp_zones`, `structural` (ISMT/SMT), swing markers — **minimal v1:** ES candles + NQ existing chart; **v2:** confluence overlays as time permits.
- **Backtest wiring:** Phase 5 `run_session_backtest` may gain optional `enhanced_charts: bool` when dual chart ready.

---

## 6. Risk: scope vs M1 “audit”

- Full confluence annotation (every ISMT/SMT field) touches `ismt.py` / `smt.py` public fields — plans should order **pytest guards first**, then **audit_report**, then **equity**, then **charts** so M1 can ship with **partial** dual charts if needed.

---

## Validation Architecture

| Dimension | Method |
|-----------|--------|
| AUDIT-02..07 | `tests/phase07/test_audit_*.py` + pytest markers optional `audit` |
| AUDIT-01 | Manual + documented; optional `@pytest.mark.integration` double-run if parquet present |
| Report | Golden string fragments in `audit_report.md` header |
| Charts | `fig.to_html()` smoke; no visual CI |

---

## RESEARCH COMPLETE

Proceed to PLAN.md authoring with **`07-CONTEXT.md`** as authority for manual vs automated split and chart layout.
