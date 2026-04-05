# PROJECT: Wicked LVN/Ledge Strategy — Automated Backtest Engine

## What This Is

An institutional-grade backtesting engine for the **Wicked LVN/Ledge Strategy**, a price-acceptance / market-structure approach that exploits Low Volume Nodes (LVNs) and thin price areas on NQ futures. The engine mechanizes the strategy rule-by-rule with zero hindsight bias, generates a ground-truth trade log, and produces institutional performance metrics.

**Primary trading instrument:** NQ (Nasdaq-100 Futures)
**Confluence instrument:** ES (S&P 500 Futures) — used exclusively for SMT divergence detection

**Two milestones:**
- **M1 — Mechanical Backtest Engine** (V1): Fully mechanized strategy → hindsight-free trade log → institutional metrics
- **M2 — ML Optimization & Monte Carlo** (V2): ML-filtered signal set → dual-instrument reality-first Monte Carlo → interactive dashboard

---

## Core Value

> **Produce a statistically sound, reproducible backtest that proves or disproves whether the Wicked LVN/Ledge strategy has a real, persistent edge on NQ — before any real capital is risked.**

If M1 is wrong, everything downstream (ML, MC, live trading) is wrong. M1 correctness is non-negotiable.

---

## Data

| Dataset | File | Shape | Date Range | Columns |
|---------|------|-------|------------|---------|
| ES (1-min) | `1Min_ES.parquet` | 4,234,977 rows × 7 cols | 2014-01-02 → 2026-01-30 | Date, Symbol, Open, High, Low, Close, Volume |
| NQ (1-min) | `nq_1min_10y.parquet` | 5,790,530 rows × 6 cols | 2008-12-11 → 2026-03-26 | open, high, low, close, volume, timestamp |

**Backtest window:** Jan 2, 2014 → Jan 30, 2026 (ES is the limiting dataset — ~12 years)
**Timezone:** Both datasets use ET (Eastern Time) — verified from session open patterns
**Column normalization:** On load, both datasets are normalized to a common schema: `{timestamp, open, high, low, close, volume}`

---

## Strategy Summary

The **Wicked LVN/Ledge Strategy** layers three confluences to generate high-probability entries on NQ, with pre-market bias filtering:

1. **Session Volume Profile (SVP)** — Full 24-hour Globex session (6 PM prior → 6 PM), not RTH-only. LVNs (Low Volume Nodes) are thin price areas that act as magnets and rejection zones.
2. **Single Prints** — Price levels visited in only one 30-minute TPO period, confirmed with <15% of average volume. Respected overnight prints are targets and bias confirmers.
3. **ISMT / SMT Divergence** — Structural confirmation that a liquidity sweep has occurred:
   - **ISMT** (Intra-Session Market Structure Twist): Two consecutive swings on NQ where SH2 > SH1 but price closes back through SH1 (bearish) or SL2 < SL1 but closes back above (bullish)
   - **SMT** (Smart Money Technique): NQ makes higher high while ES fails to confirm (bearish), or NQ makes lower low while ES fails to confirm (bullish)
   - **Signal priority:** ISMT is weighted slightly higher than SMT (ISMT has stronger single-instrument confirmation)
4. **TPO Bias** — Pre-market 30-minute bar acceptance: >55% upper = BULLISH, <45% upper = BEARISH, mid = NEUTRAL (no trades)

**Two entry models:**
- **3-Step Model**: All three confluences must align simultaneously. Full position size.
- **Aggressive Ledge** (9:25–10:00 AM window): LVN + bias only. Half position size.

**Exit management (full partial exit logic):**
- TP1: exit 60% at nearest respected SP zone
- Trail stop to breakeven on remaining 40%
- TP2: exit remaining 40% at next SP zone
- Hard stop: body closes inside LVN zone → immediate exit
- EOD: flat by 3:45 PM ET

---

## Output Directory

All run outputs: `D:\Algorithms\Wicked Backtest Results\run_YYYYMMDD_HHMMSS\`

Structure:
```
run_YYYYMMDD_HHMMSS/
├── trades.csv
├── summary.md
├── charts/trade_001.html, ...     (per-trade Plotly candlestick, M1)
├── feature_dataset.csv            (ML inputs, M2)
├── inference_log.csv              (ML predictions, M2)
├── monte_carlo_raw_paths.csv      (MC equity paths, M2)
├── dashboard.html                 (interactive Plotly dashboard, M2)
└── summary.json                   (all metrics, machine-readable)
```

---

## Codebase Structure

```
project_root/
├── main.py                     # CLI entry point
├── requirements.txt
├── .gitignore
├── src/
│   ├── core.py                 # ATR, candle math — pure functions, no state
│   ├── swings.py               # Swing high/low detection + registry
│   ├── liquidity.py            # LVN detection, filtering, real-time invalidation
│   ├── volume_profile.py       # SVP construction, POC, VAH/VAL, single prints
│   ├── tpo.py                  # TPO bias calculation (30-min bars)
│   ├── smt.py                  # SMT + ISMT detection, synchronized bar stream
│   ├── signal.py               # 3-Step Model + Aggressive Ledge entry logic
│   ├── execution.py            # TradeSetup, TradeResult, evaluate_setup
│   ├── metrics.py              # Sharpe, Sortino, Max Drawdown, Profit Factor
│   ├── plotting.py             # Per-trade HTML charts (Plotly candlestick)
│   └── ml_pipeline.py          # M2: Feature engineering, Walk-Forward, MC engine
└── data/                       # Symlink or copy of parquet files
```

---

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Both ISMT + SMT in V1 | User confirmed both needed; ISMT weighted slightly higher | — Decided |
| Full partial exit (60%/40%) | User confirmed full logic required in V1 | — Decided |
| Output dir: D:\Algorithms\Wicked Backtest Results | Separate drive, not workspace | — Decided |
| Backtest window: 2014-01-02 → 2026-01-30 | ES dataset is the limiting factor | — Decided |
| Session: 24h Globex (6PM → 6PM ET) | Strategy explicitly requires overnight context | — Decided |
| Volume distribution: uniform per bar | Best approximation without tick data | — Pending validation |
| NQ tick size: 0.25 pts ($5/tick, $20/point) | CME spec | — Decided |
| Signal priority: ISMT > SMT | User spec: ISMT slightly stronger weight | — Decided |
| MC engine: dual-instrument synchronized chunk splicing | SMT requires NQ+ES to share chunk boundaries | — Decided (M2) |
| MC scalar: lognormal (mu=0, sigma=0.3) | Matches real price move distribution | — Decided (M2) |

---

## Requirements

### Validated

- **Phase 4 (2026-04-05):** ISMT (`IsmtSignal`, D-01/D-02 window), SMT (`SmtSignal`, corr + synthetic gates, 0.3/0.1 ATR divergence), `get_structural_confirmation` (equal priority + recency, SMT tiebreak), 3-Step + Aggressive Ledge + ENTRY-05 + D-14 hooks — see `tests/phase04/` and `04-VERIFICATION.md`. *Note: Phase 4 CONTEXT uses equal ISMT/SMT priority; PROJECT.md strategy line above may still say ISMT-weighted — align in a docs pass.*

### Active

**M1 — Core Infrastructure**
- [ ] Load and normalize both ES and NQ parquet files to unified schema
- [ ] Session boundary logic: 24h Globex window (6 PM prior → 6 PM ET)
- [ ] Session Volume Profile (SVP) construction with uniform volume distribution
- [ ] LVN detection: smoothed local minima below mean − 0.5×std
- [ ] LVN Filter 1: Multi-session confluence (±2 ticks across 2 prior sessions)
- [ ] LVN Filter 2: POC proximity exclusion (3-tick radius)
- [ ] LVN Filter 3: Real-time consolidation invalidation (3 bars or 4 crossings)
- [ ] LVN Filter 4: Minimum separation (4 ticks, keep stronger)
- [ ] TPO bias calculation (30-min bars, 55%/45% thresholds)
- [ ] Single print detection (TPO count=1, volume <15% of mean)
- [ ] Single print zone grouping (min 4 ticks height)
- [ ] Overnight respect check per SP zone
- [ ] Swing high/low detection (±5-bar lookback, 4-tick min threshold, confirmed with delay)
- [ ] ISMT bullish/bearish detection (within 10 bars, <2×ATR20 sweep size)
- [ ] SMT bullish/bearish detection (synchronized NQ+ES bar stream, correlation filter ≥0.70)
- [ ] Signal priority: ISMT slightly stronger than SMT in feature weighting
- [ ] 3-Step Model entry logic (all three confluences required, bar-close confirmation)
- [ ] Aggressive Ledge entry logic (9:25–10:00 AM, LVN + bias only, 0.5× size)
- [ ] Pre-entry checklist: RR≥1.5, SL distance bounds, 3:45 PM cutoff, max 3 trades/session
- [ ] Stop loss: LVN boundary ± 0.5×ATR5, capped at 4 ticks min / 1.5×ATR20 max
- [ ] Take profit: TP1 = nearest respected SP zone (60% exit), TP2 = next SP zone (40%)
- [ ] Breakeven trail: move SL to entry after TP1 hit
- [ ] Hard stop: body closes inside LVN zone → immediate full exit
- [ ] EOD close: force-flat by 3:45 PM ET
- [ ] Position sizing: 1% risk on $100k account
- [ ] P&L calculation (long + short polarity, commission per side × 2)
- [ ] Per-trade Plotly HTML charts
- [ ] Institutional metrics: Sharpe, Sortino, Max Drawdown, Profit Factor
- [ ] Output: trades.csv, summary.md, charts/ → D:\Algorithms\Wicked Backtest Results
- [ ] Full audit checklist: reproducibility gate, divide-by-zero guards, polarity checks

**M2 — ML + Monte Carlo**
- [ ] Feature engineering: 12+ features, all lookback-safe
- [ ] Walk-forward analysis (730-day train / 180-day OOS windows)
- [ ] XGBoost classifier with Optuna hyperparameter search
- [ ] Dynamic threshold selection per walk-forward window
- [ ] Dual-instrument synchronized chunk splicing for MC
- [ ] Per-candle lognormal scalar (mu=0, sigma=0.3, shared NQ+ES)
- [ ] Full signal detection re-run on each synthetic path (reality-first)
- [ ] Slippage stress: $2–$10 per trade random
- [ ] Ruin barrier: $85k absorbing barrier from $100k start
- [ ] Dashboard: equity cone + PnL histogram + metric annotation panel
- [ ] Resume support: incremental CSV write for MC paths
- [ ] All M2 output files: feature_dataset.csv, inference_log.csv, monte_carlo_raw_paths.csv, dashboard.html, summary.json

### Out of Scope (V1)
- Live/paper trading execution — backtesting only in M1
- News calendar integration — edge case, defer to M2 or later
- Tick data feed — OHLCV uniform distribution approximation used
- Multi-instrument beyond NQ/ES pair — single pair only

### Out of Scope (V2)
- Deep learning models (LSTM, transformer) — XGBoost + RF only
- Portfolio-level optimization — single strategy only

---

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
*Last updated: 2026-04-05 after Phase 4 execution*
