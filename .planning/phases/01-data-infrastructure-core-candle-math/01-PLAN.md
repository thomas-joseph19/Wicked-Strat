# PLAN: Phase 1 — Data Infrastructure & Core Candle Math

## Objective
Establish the project structure, load and synchronize historical NQ and ES bar data with a 24-hour Globex session boundary, implement lookahead-free core math (ATR), and create stubs for all downstream strategy logic modules to enable immediate development of Phase 2.

## Requirements Addressed
- **DATA-01**: Load ES/NQ parquets and normalize to uniform schema.
- **DATA-02**: Assign session_id using 6:00 PM ET Globex boundary.
- **DATA-03**: Handle DST using `zoneinfo.ZoneInfo("America/New_York")`.
- **DATA-04**: Build synchronized dual-instrument bar stream with `is_synthetic` flag.
- **DATA-05**: Define `InstrumentConfig` (tick, point value, commission).
- **DATA-06**: Define `StrategyThresholds` config object.
- **DATA-07**: Trim backtest window to 2014-01-02 → 2026-01-30.
- **CORE-01**: `compute_atr(bars, period)` using `bars[0:i+1]` only.
- **CORE-02**: All math functions only access `data[i-N:i]` slices.
- **CORE-03**: (Stub) Volume distribution uniform per bar.

## Wave 1: Config System & Foundation
### Task 1: Create `src/config.py` and `config.yaml`
- **Action**: Implement `InstrumentConfig` and `StrategyThresholds` as `frozen=True` dataclasses. Create a YAML loader that uses `PyYAML` to read configuration at startup.
- **Read First**: `.planning/PROJECT.md` (Table of parameters), `.planning/REQUIREMENTS.md` (DATA-05, DATA-06).
- **Acceptance Criteria**:
  - `python -c "from src.config import load_config; config = load_config(); print(config.nq.tick_size)"` prints `0.25`.
  - `config.yaml` includes all threshold parameters from the specification.

### Task 2: Create all module stubs in `src/`
- **Action**: Create the following files, each containing a header comment and stubs that raise `NotImplementedError` for their respective responsibilities: `volume_profile.py`, `lvn.py`, `single_prints.py`, `tpo.py`, `swings.py`, `ismt.py`, `smt.py`, `entry.py`, `position.py`, `metrics.py`, `plotting.py`, `backtest.py`, `utils.py`, `ml_pipeline.py`.
- **Read First**: `.planning/phases/01-data-infrastructure-core-candle-math/01-CONTEXT.md` (D-10 module list).
- **Acceptance Criteria**:
  - `ls src/*.py` shows all 18 mentioned files.
  - No file contains syntax errors.

## Wave 2: Data Loader & Synchronization
### Task 1: Implement `src/data_loader.py`
- **Action**: Implement `NQDataLoader` and `ESDataLoader` classes using `pandas` (with `pyarrow` engine). Normalize column names (lowercase), rename ES `Date` to `timestamp`, cast volumes to float.
- **Read First**: `nq_1min_10y.parquet`, `1Min_ES.parquet`.
- **Acceptance Criteria**:
  - `DataLoader.load_instrument('NQ')` returns a DataFrame with `timestamp` index.
  - Schema for both DataFrames is identical: `open, high, low, close, volume`.

### Task 2: Implement Dual-Instrument Stream Synchronization
- **Action**: Perform an `outer join` on both DataFrames based on the 1-min floored timestamp. Forward-fill missing values (`method='ffill'`). Add an `is_synthetic` column using boolean masks for cases where either instrument was missing.
- **Read First**: `.planning/research/ARCHITECTURE.md` (Dual-Instrument Synchronization).
- **Acceptance Criteria**:
  - `SyncedStream.get_bars()` contains both NQ and ES columns for every row.
  - `is_synthetic_nq` and `is_synthetic_es` flags are correctly assigned to filled rows.

## Wave 3: Session Logic
### Task 1: Implement `src/session.py`
- **Action**: Implement `SessionManager` class. Create a `assign_session_id` function using `zoneinfo.ZoneInfo("America/New_York")` and the 18:00 (6 PM) ET cutoff. Group the synchronized bar stream by this `session_id`.
- **Read First**: `.planning/research/ARCHITECTURE.md` (Session Architecture).
- **Acceptance Criteria**:
  - `session_id` for a bar at 2024-01-01 17:59 is `2024-01-01`.
  - `session_id` for a bar at 2024-01-01 18:01 is `2024-01-02`.
  - The first session of the backtest is `2014-01-02`.

## Wave 4: Core Math & Backtest Entry
### Task 1: Implement Core Math in `src/core.py`
- **Action**: Implement `compute_atr(bars, period)` using only prior data. Implement True Range calculation (max of: `H-L`, `abs(H-PC)`, `abs(L-PC)`). Mask `is_synthetic` bars during computation (keep value constant or skip).
- **Read First**: `.planning/REQUIREMENTS.md` (CORE-01, CORE-02).
- **Acceptance Criteria**:
  - Unit test: `test_atr_no_lookahead` confirms that changing `bars[i+1]` does not affect `ATR[i]`.
  - `ATR_5` and `ATR_20` are computed correctly for a test session.

### Task 2: Implement `main.py` CLI
- **Action**: Create a CLI entry point using `argparse` to handle `--mode`, `--start`, and `--end` flags. Orchestrate loading config and one instrument as a smoke test.
- **Acceptance Criteria**:
  - `python main.py --mode backtest --start 2014-01-02 --end 2014-01-05` runs without error and prints total bar count.

## Verification for Phase 1
- **V-01**: Date/Time Schema verification (no UTC offsets).
- **V-02**: Session ID assignment (Globex boundary).
- **V-03**: Missing bar filling correctness.
- **V-04**: ATR lookback safety.
- **V-05**: Output dir existence check.

## Must-Haves (Goal Check)
- [ ] Both parquet files loaded and synchronized.
- [ ] Session ID assignment using 6 PM ET cutoff follows Globex rules.
- [ ] ATR-5 and ATR-20 implemented without lookahead bias.
- [ ] Stubs exist for 18 strategy modules.
