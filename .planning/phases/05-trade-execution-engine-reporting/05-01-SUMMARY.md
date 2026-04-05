# Plan 05-01 — Summary

- **Position** state machine: PENDING_FILL → OPEN_FULL → OPEN_PARTIAL → CLOSED with intrabar ordering after entry; **SessionTradeBudget** on OPEN_FULL; sizing and PnL helpers in `src/position.py`.
- Tests: `test_position_sizing.py`, `test_pnl_commission.py`, `test_position_machine_core.py` (D-05/D-06 conflict, long/short).

Verification: `python -m pytest tests/phase05/test_position_sizing.py tests/phase05/test_pnl_commission.py tests/phase05/test_position_machine_core.py -q`
