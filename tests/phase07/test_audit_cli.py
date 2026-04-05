"""audit.py report generation."""

from pathlib import Path

from src.audit import (
    AuditRow,
    audit_01_manual_row,
    run_full_checklist,
    run_programmatic_checks,
    write_audit_report,
)


def test_write_report(tmp_path: Path):
    rows = [
        AuditRow("X", "d", "PASS", "ok", "t0"),
    ]
    p = tmp_path / "r.md"
    write_audit_report(p, rows)
    text = p.read_text(encoding="utf-8")
    assert "| ID | Description | Result |" in text
    assert "AUDIT" not in text or "X" in text


def test_programmatic_all_pass():
    rows = run_programmatic_checks()
    assert len(rows) == 6
    assert all(r.result == "PASS" for r in rows)


def test_full_checklist_has_seven_ids():
    rows = run_full_checklist()
    assert len(rows) == 7
    ids = [r.audit_id for r in rows]
    assert ids[0] == "AUDIT-01"
    assert rows[0].result == "MANUAL"
    assert "backtest_results_" in rows[0].evidence or "fc /b" in rows[0].evidence


def test_audit_01_manual_row():
    r = audit_01_manual_row()
    assert r.audit_id == "AUDIT-01"
    assert r.result == "MANUAL"
