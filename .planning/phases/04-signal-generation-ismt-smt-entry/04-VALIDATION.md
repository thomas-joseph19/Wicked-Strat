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

Aligned with `04-00-PLAN.md` … `04-04-PLAN.md` frontmatter `wave` and `<verify>` / task acceptance commands.

| Task ID | Plan | Wave | Requirement(s) | Test type | Automated command | File exists | Status |
|---------|------|------|----------------|-----------|-------------------|-------------|--------|
| 4-00-01 | 00 | 0 | pytest layout | config | `python -m pytest tests/phase04/ --collect-only -q` | `pyproject.toml` | ⬜ pending |
| 4-00-02 | 00 | 0 | EXEC-01, SIG-03, fixtures | smoke + collect | `python -m pytest tests/phase04/ --collect-only -q` | `tests/phase04/conftest.py`, `src/position.py` | ⬜ pending |
| 4-01-01 | 01 | 1 | ISMT-01..03 (API) | import | `python -c "from src.ismt import IsmtSignal; print(IsmtSignal.__name__)"` | `src/ismt.py` | ⬜ pending |
| 4-01-02 | 01 | 1 | ISMT-01..03 | unit | `python -m pytest tests/phase04/test_ismt.py -q --tb=short` | `tests/phase04/test_ismt.py` | ⬜ pending |
| 4-02-01 | 02 | 1 | SMT-01, SMT-02 | import | `python -c "import importlib; importlib.import_module('src.smt')"` | `src/smt.py` | ⬜ pending |
| 4-02-02 | 02 | 1 | SMT-01..05 | unit | `python -m pytest tests/phase04/test_smt.py -q --tb=short` | `tests/phase04/test_smt.py` | ⬜ pending |
| 4-03-01 | 03 | 2 | SIG-01..03 (selector API) | import | `python -c "import importlib; importlib.import_module('src.entry')"` | `src/entry.py` | ⬜ pending |
| 4-03-02 | 03 | 2 | SIG-01..03 | unit | `python -m pytest tests/phase04/test_structural_confirmation.py -q --tb=short` | `tests/phase04/test_structural_confirmation.py` | ⬜ pending |
| 4-04-01 | 04 | 3 | ENTRY-01..05 (entry wiring) | import + grep | `python -c "import importlib; importlib.import_module('src.entry'); importlib.import_module('src.position')"` | `src/entry.py`, `src/position.py` | ⬜ pending |
| 4-04-02 | 04 | 3 | ENTRY-05 | unit | `python -m pytest tests/phase04/test_entry_checklist.py -q --tb=short` | `tests/phase04/test_entry_checklist.py` | ⬜ pending |
| 4-04-03 | 04 | 3 | ENTRY-01..04, D-14 | unit | `python -m pytest tests/phase04/test_entry_three_step.py tests/phase04/test_entry_aggressive_ledge.py -q --tb=short` | `test_entry_three_step.py`, `test_entry_aggressive_ledge.py` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/phase04/conftest.py` — minimal bar streams, swing/LVN/SP stubs
- [ ] `tests/phase04/__init__.py` — package marker
- [ ] `pyproject.toml` — pytest config + dev dependency group
- [ ] `src/position.py` — `TradeSetup` + Phase 5 stubs including `enter_from_setup` hook per `04-04-PLAN.md`

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
