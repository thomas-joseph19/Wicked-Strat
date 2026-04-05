# Plan 07-00 — Summary

- **`tests/phase07/test_audit_regression.py`**: AUDIT-02 (`validate_pre_entry`, risk≤0), AUDIT-03 (short gross PnL), AUDIT-04 (`max_drawdown_stats`), AUDIT-05 (`build_tpo_profile` resample kwargs + behavioral), AUDIT-06 (3 fills TP path, 2 fills SL path), AUDIT-07 (exact TP1/SL prices).
- **AUDIT-02**: Guard already in **`validate_pre_entry`** via **`risk <= 0`**; no **`entry.py`** change required.

Verification: `python -m pytest tests/phase07/test_audit_regression.py -q`
