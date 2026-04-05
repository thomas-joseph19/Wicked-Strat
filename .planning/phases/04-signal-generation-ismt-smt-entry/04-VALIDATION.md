---
phase: 4
slug: signal-generation-ismt-smt-entry
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-05
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pyproject.toml` (Wave 0 adds `[tool.pytest.ini_options]`) |
| **Quick run command** | `python -m pytest tests/phase04/ -q` |
| **Full suite command** | `python -m pytest tests/ -q` |
| **Estimated runtime** | ~15–45 seconds (grows with suite) |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/phase04/ -q`
- **After every plan wave:** Run `python -m pytest tests/ -q`
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 4-01-01 | 01 | 1 | ISMT-01, ISMT-02 | unit | `python -m pytest tests/phase04/test_ismt.py -q` | ❌ W0 | ⬜ pending |
| 4-01-02 | 01 | 1 | ISMT-03 | unit | `python -m pytest tests/phase04/test_ismt.py::test_ismt_signal_fields -q` | ❌ W0 | ⬜ pending |
| 4-02-01 | 02 | 1 | SMT-01, SMT-02 | unit | `python -m pytest tests/phase04/test_smt_correlation.py -q` | ❌ W0 | ⬜ pending |
| 4-02-02 | 02 | 1 | SMT-03, SMT-04, SMT-05 | unit | `python -m pytest tests/phase04/test_smt_divergence.py -q` | ❌ W0 | ⬜ pending |
| 4-03-01 | 03 | 2 | SIG-01, SIG-02, SIG-03 | unit | `python -m pytest tests/phase04/test_structural_confirmation.py -q` | ❌ W0 | ⬜ pending |
| 4-04-01 | 04 | 2 | ENTRY-01, ENTRY-02 | unit | `python -m pytest tests/phase04/test_entry_three_step.py -q` | ❌ W0 | ⬜ pending |
| 4-04-02 | 04 | 2 | ENTRY-03, ENTRY-04, ENTRY-05 | unit | `python -m pytest tests/phase04/test_entry_aggressive_ledge.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/phase04/conftest.py` — minimal bar streams, swing/LVN/SP stubs
- [ ] `tests/phase04/__init__.py` — package marker
- [ ] `pyproject.toml` — pytest config + dev dependency group

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Chart/visual parity | — | N/A for Phase 4 | None — reporting is Phase 5 |

*All phase behaviors targeted for automated verification via constructible bar streams (see 04-RESEARCH.md Validation Architecture).*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
