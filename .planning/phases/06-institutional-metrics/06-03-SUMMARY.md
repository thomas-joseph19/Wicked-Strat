# Plan 06-03 — Summary

- **`compute_and_write_institutional_summaries`** in `src/metrics.py` (lazy import of `summary_report`).
- **`run_session_backtest(..., write_institutional_summaries=False, config_path=...)`** in `src/backtest.py`.
- **Tests**: `tests/phase06/test_metrics_backtest_wiring.py`; `pytest_plugins` in `tests/phase06/conftest.py` for Phase 5 fixtures.

Verification: `python -m pytest tests/phase06/ tests/phase05/test_summary_stub.py -q`
