---
phase: 04-signal-generation-ismt-smt-entry
plan: "02"
requirements-completed: [SMT-01, SMT-02, SMT-03, SMT-04, SMT-05]
completed: 2026-04-05
---

# Phase 4 Plan 02 — Summary

`SmtSignal` + `detect_smt_at_bar`: 20-return Pearson via `numpy.corrcoef`, synthetic window >2 skip, P7 per-leg synthetic at bar, divergence 0.3/0.1×ATR20, ±3 bar swing alignment. Tests in `tests/phase04/test_smt.py`.
