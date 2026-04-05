# Plan 07-01 — Summary

- **`src/audit.py`**: `AuditRow`, `write_audit_report`, `run_programmatic_checks`, `run_full_checklist`, **AUDIT-01** MANUAL row, CLI `--out`.
- **`tests/phase07/test_audit_cli.py`**.

Verification: `python -m pytest tests/phase07/test_audit_cli.py -q` and `python -m src.audit --out audit_report.md` (repo root, `PYTHONPATH=.` or `pip install -e .`)
