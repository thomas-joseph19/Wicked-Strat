<!-- GSD:project-start source:PROJECT.md -->
## Project

**PROJECT: Wicked LVN/Ledge Strategy — Automated Backtest Engine**

An institutional-grade backtesting engine for the **Wicked LVN/Ledge Strategy**, a price-acceptance / market-structure approach that exploits Low Volume Nodes (LVNs) and thin price areas on NQ futures. The engine mechanizes the strategy rule-by-rule with zero hindsight bias, generates a ground-truth trade log, and produces institutional performance metrics.

**Primary trading instrument:** NQ (Nasdaq-100 Futures)
**Confluence instrument:** ES (S&P 500 Futures) — used exclusively for SMT divergence detection

**Two milestones:**
- **M1 — Mechanical Backtest Engine** (V1): Fully mechanized strategy → hindsight-free trade log → institutional metrics
- **M2 — ML Optimization & Monte Carlo** (V2): ML-filtered signal set → dual-instrument reality-first Monte Carlo → interactive dashboard

---

**Core Value:** > **Produce a statistically sound, reproducible backtest that proves or disproves whether the Wicked LVN/Ledge strategy has a real, persistent edge on NQ — before any real capital is risked.**

If M1 is wrong, everything downstream (ML, MC, live trading) is wrong. M1 correctness is non-negotiable.

---
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Recommended Stack
| Component | Library | Version |
|-----------|---------|---------|
| Data I/O | `pandas` + `pyarrow` | pandas 2.x, pyarrow 13+ |
| Numerics | `numpy` | 1.26+ |
| Timezone | `zoneinfo` (stdlib) | Python 3.9+ |
| Charting | `plotly` | 5.x |
| ML | `xgboost` | 2.x |
| Hypertuning | `optuna` | 3.x |
| Walk-forward | Custom (see Architecture) | — |
| Market calendars | `pandas_market_calendars` | 4.x |
## Library Rationale
### pandas + pyarrow (NOT polars for this project)
- Session groupby + iteration is idiomatic in pandas
- The strategy's bar-by-bar state is inherently sequential — vectorization is limited
- pyarrow handles Parquet I/O efficiently (both files < 100MB)
- The team's existing code context is pandas-based
### numpy
### zoneinfo (NOT pytz)
### Plotly
### XGBoost + Optuna (M2)
### pandas_market_calendars
## What NOT to Use and Why
| Library | Reason to Avoid |
|---------|----------------|
| Polars | No advantage for stateful bar-by-bar session loops; adds complexity |
| Backtrader | Aging architecture; poor multi-instrument synchronization; slow |
| vectorbt | Vectorized-only; lookahead bias is extremely easy to introduce in complex multi-condition strategies |
| Nautilus Trader | Overkill; designed for live execution, not pure backtesting scripts |
| Numba | Adds JIT compilation complexity without meaningful gain at 4M rows with session iteration |
| pytz | Deprecated in favor of zoneinfo; still works but unnecessary |
## Confidence Levels
| Recommendation | Confidence | Notes |
|---------------|------------|-------|
| pandas + numpy for core loop | HIGH | Proven pattern for this complexity level |
| zoneinfo for timezone | HIGH | stdlib, no dependencies |
| plotly for charts | HIGH | Only HTML-output charting library that produces standalone files |
| XGBoost + Optuna | HIGH | Industry standard for tabular ML in finance |
| pandas_market_calendars | MEDIUM | Verify CME calendar has correct early-close dates for 2014-2026 |
| Session-by-session iteration (not vectorized) | HIGH | Vectorizing this strategy's conditions without lookahead is nearly impossible |
## Performance Notes
- At 4M rows × 2 instruments = ~8M total bars: fits comfortably in RAM as float32 (~500MB)
- Process session-by-session, not all at once: use `.groupby()` on session_id column
- Pre-compute session_id by flooring timestamp to session boundary (6PM ET)
- gc.collect() after each walk-forward window (M2 only)
- numpy arrays for ATR/volume computations, not DataFrame operations in inner loops
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
