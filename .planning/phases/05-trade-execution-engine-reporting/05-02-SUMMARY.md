# Plan 05-02 — Summary

- **EOD** and **HARD_STOP_LVN** evaluated before TP/SL in `_update_open` (`body_inside_lvn`, `bar_is_eod`).
- Tests: `test_hard_stop_lvn.py`, `test_eod_force_flat.py`, `test_full_exit_ordering.py` (EOD vs TP1, hard stop vs TP2, D-05/D-06 regression).

Verification: `python -m pytest tests/phase05/test_hard_stop_lvn.py tests/phase05/test_eod_force_flat.py tests/phase05/test_full_exit_ordering.py -q`
