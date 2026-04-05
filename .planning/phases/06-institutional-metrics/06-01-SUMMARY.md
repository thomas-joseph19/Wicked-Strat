# Plan 06-01 — Summary

- **`sharpe_ratio_annualized`** (ddof=1), **`sortino_ratio_annualized`** (D-07 tuple + downside-empty flag), **`calmar_ratio`**, **`recovery_factor`**, **`annual_breakdown`**.
- **Tests**: `tests/phase06/test_sharpe_sortino_calmar.py`.

Verification: `python -m pytest tests/phase06/test_sharpe_sortino_calmar.py -q`
