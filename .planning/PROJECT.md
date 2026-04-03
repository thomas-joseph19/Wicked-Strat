# Wicked LVN/Ledge Strategy

## What This Is
An automated trading agent explicitly designed to exploit market structure rejections at Low Volume Nodes (LVNs) and single prints, combined with ISMT/SMT divergence. Version 1 focuses on strict mechanical automation of the pre-defined 3-step strategy rules using provided 1-minute historical data.

## Core Value
High-precision, mathematically rigorous entries based on volume anomaly rejections, eliminating qualitative or hindsight-biased discretionary entries.

## Context
- The algorithm targets the NQ/ES futures markets (primarily using 1-minute OHLCV data).
- The strategy utilizes multi-session Volume Profiles (SVP), TPO (Time Price Opportunity) distributions, and swing divergence (ISMT).
- An existing 10-year dataset (`nq_1min_10y.parquet`) with OHLCV data is available for V1 backtesting.

## Definitions
- **LVN (Low Volume Node):** A price level with statistically low volume, acting as a magnet/rejection zone.
- **Single Print:** A price level visited exactly once during a 30-minute TPO period.
- **ISMT:** Intra-Session Market Structure Twist — a pattern of divergence signaling a liquidity sweep trap.
- **POC:** Point of Control (highest volume price level).
- **SVP:** Session Volume Profile (anchored to 6:00 PM ET to 6:00 PM ET 24h window).

## Requirements

### Validated
- ✓ [Ingestion Pipeline] — Ingest 10y NQ data with timezone-aware session bounds and integer scaling (Phase 1)
- ✓ [Volume Profile Engine] — Interpolate tick volume, compute POC/VA, and detect raw statistical LVNs (Phase 2)
- ✓ [Structure & Filtering] — Multi-session confluence, Behavioral Invalidation, and TPO daily bias (Phase 3-4)
- ✓ [Technical Analysis] — ATR-normalized swings and ISMT Trap-and-Reverse detection (Phase 5)
- ✓ [Simulation] — End-to-end backtest generator with PnL, Win-Rate, and Drawdown (Phase 6-7)

### Active
- [ ] Construct multi-session Session Volume Profiles algorithmically from 1-min data.
- [ ] Determine Low Volume Node candidates with multi-session conflunce and invalidation tracking.
- [ ] Implement TPO calculation over 30-minute intervals to define daily market bias.
- [ ] Identify single prints correctly, evaluating overnight behavior.
- [ ] Detect valid ISMT (Intra-Session Market Structure Twist) patterns based on parameterized ATR filters and swing high/low logic.
- [ ] Build the 3-Step Model execution logic for the strategy.
- [ ] Build the Aggressive Ledge execution logic for the 9:30 AM open window.
- [ ] Develop the backtesting engine (via Python vectorization/Polars or a framework like VectorBT) incorporating strict rule enforcement and preventing hindsight bias.
- [ ] Output backtesting metrics and standard performance analytics.

### Out of Scope
- Machine learning optimizations. (Saved for V2).
- Options or stock trading integrations. (Designed strictly for NQ/ES futures for now).
- Arbitrary timeframe analysis aside from 1-min and 30-min definitions.

## Key Decisions
| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python + Polars/Pandas Stack | Given the large dataset (10y of 1-minute OHLCV data) and the intensive array manipulations for profile math, a high-performance dataframe library is required. | Pending |
| Tick Volume Mathematical Breakdown | Provide a fallback to approximate tick volume when tick data isn't natively exported. | Pending |

## Evolution
This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Project lifecycle: Completed 2026-04-03 after Phase 7 results.*
