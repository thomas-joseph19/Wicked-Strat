# Plan 05-00 — Summary

- **TradeSetup** includes required `tp2_price`; **entry** computes TP2 via `compute_tp2_long` / `compute_tp2_short` (TP-02).
- **RunPaths** / `make_run_paths` / `run_paths_from_config` in `src/config.py` (D-14/D-15 layout).
- Phase 5 tests: TP2/SL contract, run paths, and shared `conftest` factories (`simple_setup` default LVN placed away from price so generic tests do not hit hard-stop).

Verification: `python -m pytest tests/phase05/test_tp2_and_sl_contract.py tests/phase05/test_run_paths.py -q`
