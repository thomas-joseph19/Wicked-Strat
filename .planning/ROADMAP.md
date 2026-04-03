# Roadmap: Wicked LVN/Ledge Strategy

**Goal:** Implement a fully automated, strictly mechanical backtesting engine over a 10-year 1-min NQ market data parquet to analyze the Wicked LVN/Ledge strategy.

## Phase 1: Context & Data Ingestion Pipeline
**Goal:** Setup repository, parse the 10-year parquet structure, and build the foundational UTC-to-ET timezone 6 PM session boundaries logic.
- Plan 1: Define environment constraints, import the `nq_1min_10y.parquet` with Polars/Pandas, ensuring floats convert properly to stable integer-scaled indexes for tick alignment.
- Plan 2: Build the session slice iterator that properly partitions raw data by the 6 PM ET to 6 PM ET continuous chunks, preparing cleanly separated day frames.

## Phase 2: Core Computations I (Raw Profile Engine)
**Goal:** Mathematically process raw 1-minute bars into synthetic tick distributions to establish the initial Session Volume Profile (SVP).
- Plan 1: Write the interpolation algorithm to allocate 1-min volume uniformly across the tick spread of low to high.
- Plan 2: Calculate generic SVP metrics accurately for the 24h span (POC, V_total, V_mean, V_fixed_std_dev, Value Areas).
- Plan 3: Formulate Raw LVN detection (3-tick moving averages, local minimums combined with deviation threshold).

## Phase 3: Core Computations II (Multi-Session Filters)
**Goal:** Implement the rigorous LVN filtering logic across consecutive data arrays to distill thousands of raw LVNs down to tradeable structures.
- Plan 1: Build the multi-session alignment filter mapping (-1, -2 session LVNs) mapping overlaps mapping ±2 ticks.
- Plan 2: Build real-time LVN invalidation logic enforcing consolidation thresholds and cross thresholds tracking per LVN zone as price drifts through it.
- Plan 3: Apply minimum 4-tick separation rules discarding weakly clustered LVNs.

## Phase 4: Core Computations III (TPO & Single Prints)
**Goal:** Create the independent array computations for daily directional bias via TPO distributions, capturing single prints logic and overnight behavior.
- Plan 1: Generate 30-min price-slice visitation matrices per session to structure TPO logic to determine Daily Bias (upper_ratio > 0.55).
- Plan 2: Apply the mathematical filters for discovering and indexing gap-like single prints (< 0.15 V_mean validation).
- Plan 3: Filter single prints logically by implementing overnight (post 6 PM pre 9:30 AM) price rejection tracking per zone.

## Phase 5: Technical Analysis (Swings & ISMT Patterns)
**Goal:** Add dynamic swing markers and ATR engines for final divergence validation necessary for the 3-Step entry model.
- Plan 1: Build a rolling ATR (5 and 20) matrix calculation tool.
- Plan 2: Code the `swing_high` and `swing_low` parameter tests with structural validation loops checking against defined localized extremums.
- Plan 3: Construct the boolean detector for `ISMT` (Intra-Session Market Structure Twists) parsing consecutive overlapping/diverging swing configurations.

## Phase 6: Core Strategy Logic & Entry Detection
**Goal:** Aggregate inputs to trigger precise non-discretionary simulated execution triggers.
- Plan 1: Implement the Aggressive Ledge strategy matrix detecting LVN + defined Bias combinations isolated strictly between 9:25 - 10:00 AM ET.
- Plan 2: Implement the full 3-Step Model logic (Bias + Active LVN support/resistance + Confirmed ISMT < 5 ticks away + Single Print target).

## Phase 7: Simulation Framework & Metrics Engine
**Goal:** Design the order traversal framework evaluating risk parameters simulating sequential timeline fills and taking profit targets.
- Plan 1: Develop the internal simulator evaluating the 1.5 Minimum R:R dynamic requirement across the generated targets + dynamically driven stop zones (LVN_high/low + ATR buffer).
- Plan 2: Write logic computing simulated execution, taking 60% partial at Target 1 and moving SL to Break Even. Write real-time hard-stop checks (candle body fully absorbing LVN execution zones).
- Plan 3: Aggregate executed simulated trades resolving to performance outputs (Total P/L, Winrate, Expected Value, etc.).

---

*End of Document. Begin `/gsd-plan-phase 1` to commence development of the initial context module when ready.*
