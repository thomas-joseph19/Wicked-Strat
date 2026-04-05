---
phase: 7
slug: trade-logic-audit-verification
status: draft
nyquist_compliant: false
created: 2026-04-05
---

# Phase 7 — Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Quick command** | `python -m pytest tests/phase07/ -q` |
| **Full suite** | `python -m pytest tests/ -q` |
| **Audit CLI** | `python -m src.audit` or `python src/audit.py` (per PLAN) |

## Per-Plan Map

| Plan | AUDIT IDs | Primary verification |
|------|-----------|----------------------|
| 07-00 | AUDIT-02,03,04,05,06,07 | pytest phase07 + referenced phase05/06 |
| 07-01 | AUDIT-01 (manual doc), all (report rows) | `audit_report.md` exists + row count |
| 07-02 | (supporting) | equity HTML smoke |
| 07-03 | (supporting D-07–D-09) | dual-chart `to_html` smoke |

## Manual-Only

| Item | Reason |
|------|--------|
| AUDIT-01 byte-identical full run | Two long backtests + diff per D-01/D-02 |
| Browser review of Plotly | Optional |

## Sign-Off

**Approval:** pending
