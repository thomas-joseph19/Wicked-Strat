# ARCHITECTURE.md — Backtesting Engine Design

## Component Boundaries

```
┌─────────────────────────────────────────────────────────────────┐
│  main.py  —  CLI entry, argument parsing, run orchestration     │
└───────────────────────────────┬─────────────────────────────────┘
                                │
              ┌─────────────────▼──────────────────┐
              │  Data Layer (data_loader.py)         │
              │  - Load ES + NQ parquet              │
              │  - Normalize to common schema        │
              │  - Assign session_id to each bar     │
              │  - Build synchronized NQ+ES pairs    │
              └─────────────────┬──────────────────┘
                                │
              ┌─────────────────▼──────────────────┐
              │  Session Iterator                    │
              │  - Group bars by session_id          │
              │  - Stream one session at a time      │
              │  - Prior session context (2 back)    │
              └─────────────────┬──────────────────┘
                                │
         ┌──────────────────────▼─────────────────────┐
         │  Pre-Market Phase (runs before 9:30 AM)     │
         │                                             │
         │  volume_profile.py  → SVP construction      │
         │                     → POC, VAH, VAL         │
         │                     → LVN candidates        │
         │  liquidity.py       → LVN filtering (4 steps)│
         │  tpo.py             → TPO bias (30-min bars)│
         │  volume_profile.py  → Single print detection│
         │                     → Overnight respect     │
         └──────────────────────┬─────────────────────┘
                                │
         ┌──────────────────────▼─────────────────────┐
         │  RTH Execution Phase (9:30 AM → 3:45 PM)   │
         │                                             │
         │  core.py      → ATR_5, ATR_20 per bar       │
         │  swings.py    → Swing detection (confirmed) │
         │  smt.py       → ISMT + SMT detection        │
         │  signal.py    → Entry condition checking    │
         │  execution.py → Position state, bar-by-bar  │
         │  liquidity.py → LVN consolidation update    │
         └──────────────────────┬─────────────────────┘
                                │
         ┌──────────────────────▼─────────────────────┐
         │  Output Layer                               │
         │  plotting.py  → Per-trade HTML charts       │
         │  metrics.py   → Sharpe, Sortino, etc.       │
         │  → trades.csv, summary.md                   │
         └─────────────────────────────────────────────┘
```

## Data Flow

```
ES Parquet ──┐
             ├── Normalize columns → session_id → Synchronized pairs
NQ Parquet ──┘
                       │
              ┌────────▼────────┐
              │ Session groups   │   ← Group by session_id, iterate
              └────────┬────────┘
                       │   For each session:
                       ▼
              Pre-market bars ──► SVP ──► LVNs ──► Filtered LVNs
                                 ├──► POC
                                 ├──► Single prints ──► SP zones
                                 └──► TPO bias (if neutral: skip session)
                       │
              RTH bars (bar by bar) ──► LVN validity update
                                    ──► ATR calculations
                                    ──► Swing detection (confirmed_at)
                                    ──► ISMT check
                                    ──► SMT check (NQ+ES correlated)
                                    ──► Entry signal check
                                    ──► Position update (if open)
                                    ──► Fill events → trades
```

## Build Order (Phase Dependencies)

```
Phase 1: Data Infrastructure
  - Parquet loading + normalization
  - Session boundary logic
  - Synchronized NQ/ES stream
  ↓
Phase 2: Swing Detection + Bias
  - Swing high/low (confirmed_at delay)
  - TPO bias (30-min bars)
  - ATR calculations
  ↓
Phase 3: Volume Profile + LVN + Single Prints
  - SVP construction
  - LVN detection + all 4 filters
  - Single print detection + overnight respect
  ↓
Phase 4: Signal Generation (ISMT + SMT + Entry)
  - ISMT detection (single instrument)
  - SMT detection (dual instrument synchronized)
  - 3-Step Model entry logic
  - Aggressive Ledge entry logic
  ↓
Phase 5: Execution Engine + Reporting
  - TradeSetup, TradeResult
  - Bar-by-bar position management
  - Partial exits (60%/40%)
  - Hard stop, EOD close
  - Plotly per-trade charts
  ↓
Phase 6: Metrics
  - Daily PnL aggregation
  - Sharpe, Sortino, Max Drawdown, Profit Factor
  ↓
Phase 7: Audit + Reproducibility
  - Full checklist validation
  - Dual-run reproducibility gate
```

## Session Architecture

```python
# Session boundary definition
# Session N: prev_day 18:00 ET → current_day 18:00 ET (24h window)

def assign_session_id(timestamp_et):
    """
    A bar at 2025-04-04 15:00 ET → session '2025-04-04'
    A bar at 2025-04-04 19:00 ET → session '2025-04-05'  ← next session starts at 18:00
    """
    session_cutoff = timestamp_et.replace(hour=18, minute=0, second=0, microsecond=0)
    if timestamp_et >= session_cutoff:
        return (timestamp_et + timedelta(days=1)).date().isoformat()
    return timestamp_et.date().isoformat()
```

Session phases:
- **Overnight**: 18:00 → 09:29 ET (SVP builds, SP respect check occurs)
- **Pre-market computation**: At 09:29 freeze the pre-RTH profile and compute bias/LVNs/SP zones
- **RTH**: 09:30 → 15:45 ET (execution window)
- **Aggressive window**: 09:25 → 10:00 ET (within RTH, extra entry model)
- **EOD cutoff**: 15:45 ET (force-close all positions)

## Dual-Instrument Synchronization

```
NQ bars: [09:30, 09:31, 09:32, _________, 09:34, ...]
ES bars: [09:30, 09:31, 09:32, 09:33, 09:34, ...]

Problem: NQ missing 09:33 bar
Solution: floor timestamps to minute, forward-fill missing bars
          Mark synthetic bars (is_synthetic=True)
          Never trigger SMT on synthetic bar pairs
```

Key rule: **Swing high/low detection runs on each instrument's full bar array independently.** The SMT comparison happens only at the signal-detection level, using confirmed swings from each instrument's registry.

## Resumability Pattern

For the full 12-year backtest (M1):
- Process year-by-year, append results to trades.csv after each year
- Session state is stateless between sessions (no cross-session carry-over by design)
- If interrupted, re-run from the last completed year boundary

For M2 (ML walk-forward + MC):
- Walk-forward: append predictions to inference_log.csv after each window
- Monte Carlo: write path equity data after each path with path_id
- On resume: skip already-completed windows/paths by checking existing CSV records

## Anti-Patterns to Avoid

1. **Loading all bars at once into a DataFrame and vectorizing signals** — creates lookahead bias
2. **Using session-end POC to make pre-RTH decisions** — POC only valid from prior session
3. **Computing swing detection on a sliding window that crosses midnight** — use session-isolated swing registries
4. **Sharing LVN zone objects across sessions** — each session gets fresh zones; no carry-over
5. **SMT correlation computed on data that spans the session maintenance gap** — skip correlation computation at session boundaries
