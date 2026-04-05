---
phase: 04
status: passed
verified: 2026-04-05
---

# Phase 4 — Verification

## Automated

- `python -m pytest tests/phase04/ -q` — all green (ISMT, SMT, structural confirmation, entry, checklist).

## Must-haves (from plans)

- ISMT window anchored to `SH2.confirmed_at + 1..+3`; sweep `< 2×ATR20`.
- SMT: corr ≥ 0.70 on 20 returns; >2 synthetic in window → skip; synthetic at eval bar → skip; 0.3/0.1 ATR divergence; ±3 bar alignment.
- Structural: [i-4, i] inclusive; recency tiebreak; SMT wins tie on same `confirmed_at`; `signal_source` ISMT=1, SMT=0.
- 3-Step: D-08 approach + structural + SP + LVN validity; Aggressive: time window, no structural, `position_size_scale=0.5`; ENTRY-05 numeric gates; D-14 suppression only after `enter_from_setup` → `notify_aggressive_trade_completed`.

## Notes

- `WindowConfig.AGGRESSIVE_START` set to `09:30` ET so ROADMAP success criterion #5 (09:28 rejected, 09:32 accepted) holds; CONTEXT still mentions 9:25 — reconcile in a docs pass if needed.
