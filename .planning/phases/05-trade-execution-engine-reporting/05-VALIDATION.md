---
phase: 5
slug: trade-execution-engine-reporting
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-05
---

# Phase 5 — Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `python -m pytest tests/phase05/ -q` |
| **Full suite command** | `python -m pytest tests/ -q` |
| **Estimated runtime** | ~20–60 seconds |

## Sampling Rate

- After every task commit: `python -m pytest tests/phase05/ -q`
- After each wave: `python -m pytest tests/ -q`

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement cluster | Automated Command | Status |
|---------|------|------|----------------------|-------------------|--------|
| 5-00-01 | 00 | 0 | harness | `python -m pytest tests/phase05/ --collect-only -q` | ⬜ |
| 5-01-xx | 01 | 1 | EXEC, SL, partial fills | `python -m pytest tests/phase05/test_position_sm.py -q` | ⬜ |
| 5-02-xx | 02 | 1 | TP, hard stop, EOD | `python -m pytest tests/phase05/test_exits.py -q` | ⬜ |
| 5-03-xx | 03 | 2 | REPORT, plotting | `python -m pytest tests/phase05/test_reporting.py -q` | ⬜ |

*Planner will align exact filenames to PLAN tasks.*

## Wave 0 Requirements

- [ ] `tests/phase05/conftest.py` — bars, TradeSetup with tp2, InstrumentConfig stubs
- [ ] Injectable `output_root` for all file writers

## Manual-Only Verifications

| Behavior | Why manual |
|----------|------------|
| Browser visual check of Plotly HTML | Optional smoke; automated asserts on file + trace names |

## Validation Sign-Off

**Approval:** pending
