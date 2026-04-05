---
phase: 6
slug: institutional-metrics
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-05
---

# Phase 6 — Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `python -m pytest tests/phase06/ -q` |
| **Full suite command** | `python -m pytest tests/ -q` |
| **Estimated runtime** | ~10–40 seconds |

## Sampling Rate

- After every task: `python -m pytest tests/phase06/ -q`
- After phase complete: `python -m pytest tests/ -q`

## Per-Plan Verification Map

| Plan | Wave | Requirement IDs | Automated Command | Status |
|------|------|-----------------|-------------------|--------|
| 06-00 | 1 | METRIC-01, METRIC-04, METRIC-05, METRIC-06 | `python -m pytest tests/phase06/test_daily_equity_drawdown_pf.py -q` | ⬜ |
| 06-01 | 2 | METRIC-02, METRIC-03 | `python -m pytest tests/phase06/test_sharpe_sortino_calmar.py -q` | ⬜ |
| 06-02 | 3 | METRIC-01..06 (reporting) | `python -m pytest tests/phase06/test_summary_markdown_json.py -q` | ⬜ |
| 06-03 | 4 | integration | `python -m pytest tests/phase06/test_metrics_backtest_wiring.py -q` | ⬜ |

## Manual-Only Verifications

| Behavior | Why manual |
|----------|------------|
| Readability of 9-section narrative | Subjective; spot-check once |

## Validation Sign-Off

**Approval:** pending
