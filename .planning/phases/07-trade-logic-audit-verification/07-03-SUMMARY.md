# Plan 07-03 — Summary

- **`TradeChartContext`**, **`build_trade_chart_dual`** (NQ row1 + ES row2 + SVP col2, SP rects, bias title).
- **`run_session_backtest(..., use_dual_charts=False, chart_ctx=None)`**.

Verification: `python -m pytest tests/phase07/test_dual_chart_smoke.py -q`
