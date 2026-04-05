# Plan 05-03 — Summary

- **plotly** added to `pyproject.toml`; `src/plotting.py` — `build_trade_chart` (candlestick + horizontal SVP, overlays, D-11 title).
- `src/reporting.py` — **RunWriter** (`append_trade_csv`, `write_trade_html`, `finalize_summary`), D-14 chart filenames.
- `src/backtest.py` — `run_session_backtest` wires Position, charts, and CSV per closed trade.
- Tests: `test_plotting_smoke.py`, `test_reporting_csv_html.py`, `test_summary_stub.py`.

Verification: `python -m pytest tests/phase05/ -q` and `python -m pytest tests/ -q`
