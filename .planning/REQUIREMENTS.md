# Requirements: Wicked LVN/Ledge Strategy

## Core Objectives
Implement a robust, purely mechanical backtesting engine for the Wicked LVN/Ledge strategy across a 10-year 1-min NQ dataset (`nq_1min_10y.parquet`). The engine must algorithmically calculate Session Volume Profiles (6 PM to 6 PM), Time Price Opportunity (TPO), Single Print tracking, and ISMT (Intra-Session Market Structure Twist) patterns, simulating the aggressive ledge and standard 3-step operational models with ZERO hindsight bias.

---

## Functional Requirements

### 1. Data Ingestion & Sanitization
*   [x] **Req 1.1:** Successfully load and parse `nq_1min_10y.parquet`. (Phase 1)
*   [x] **Req 1.2:** Handle UTC to Eastern Time timezone conversions properly, especially concerning the 6:00 PM ET operational bounds. (Phase 1)
*   [x] **Req 1.3:** Convert floats to fixed-integer precision (e.g., price * 100) to ensure zero indexing collisions or float-point errors for tick generation (0.25 tick). (Phase 1)

### 2. Volume Profile & Structure Components
*   **Req 2.1:** Distribute 1-min bar volume linearly across all price levels (`low` to `high` inclusive) within a bar to create synthetic tick volume.
*   **Req 2.2:** Calculate 24-hour windowed SVP (6 PM to 6 PM ET), computing V_total, VAV (70%), VAH, VAL, and the POC.
*   **Req 2.3:** Detect Raw LVNs utilizing the 3-tick rolling average and statistical deviation thresholds defined in the spec.
*   **Req 2.4:** Filter LVNs across mutli-sessions (prior 2 sessions mapping), POC proximity, minimum separation, and real-time consolidation invalidation.
*   **Req 2.5:** Calculate 30-min interval TPO distributions accurately (tracking session midpoint splits to evaluate 0.55 / 0.45 threshold daily bias).
*   **Req 2.6:** Detect single prints and single print zones, applying the < 0.15 V_mean volume confirmation and verifying overnight behavior respect logic.

### 3. Divergence & Signal Models
*   **Req 3.1:** Dynamically calculate the 5-bar and 20-bar ATR values.
*   **Req 3.2:** Filter and label swing highs and swing lows using the customizable ATR-driven `SWING_THRESHOLD` parameter across a 10-bar view (5 forward/back).
*   **Req 3.3:** Correctly identify and isolate ISMT setups (sweep of highs/lows with contrasting bar closures under 2 ATR size limits).

### 4. Trade Execution & Simulation Logic
*   **Req 4.1:** Verify entries chronologically and prevent *all* forms of Look-Ahead Bias. Profiling signals must strictly observe closed-bar math.
*   **Req 4.2:** Support the Agreesive Ledge entry sequence (9:25-10:00 AM ET window) using TPO bias and single active LVN conflunce.
*   **Req 4.3:** Support the complete 3-Step Model combining Bias, ISMT, LVN Confluence, and Single Print targets.
*   **Req 4.4:** Check for the 1.5 Risk-Reward ratio before releasing market orders.
*   **Req 4.5:** Properly allocate Take Profit ranges using Single Print structural bands, applying 60% partial closures and breaking-even logic.
*   **Req 4.6:** Execute dynamic Stop Losses mapping to LVN zones combined with internal closing hard-stop limits.

### 5. Outputs
*   **Req 5.1:** Produce a clear backtest reporting block including total trades, win rate, average profit, average loss, total PnL, and max drawdown.

---

## Technical Constraints
*   Must utilize **Python** with **Pandas/Polars** optimized pipelines, due to 10-year 1-min array processing. Loop-based simulation must be tightly coupled and optimized via vectorization or JIT compiler strategies (Numba/Cython) where array iterators become a bottleneck.
*   Data footprint mapping MUST correctly process the Globex operational gap rules (6:00 PM session starts).

## Out of Scope
*   Live trade integrations (IBKR / Tradovate APIs).
*   Machine learning refinements.
*   Any non-mechanical or discretionary elements.
