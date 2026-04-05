# FEATURES.md — Implementation Edge Cases & Strategy Details

## Session Boundary Management

### Globex Cycle (Critical)
- Session = 6:00 PM ET prior day → 6:00 PM ET current day (24 hours)
- Daily maintenance halt: 5:00 PM → 6:00 PM ET (no bars, no volume) — do nothing, not a gap
- Sunday open: Globex opens 6:00 PM ET Sunday (first session of the week)
- Friday close: Globex closes 5:00 PM ET Friday (no session Saturday)
- **Common mistake**: Defining session as RTH only (9:30–4:00 PM) — destroys overnight SP zone detection

### Holiday Calendar
Use `pandas_market_calendars` with the `CME` calendar:
- Full holidays: no session at all (e.g., Christmas Day)
- Early closes: session ends early (e.g., day before Thanksgiving closes at 1:00 PM ET)
- **Common mistake**: Building a partial profile on an early-close day and treating it as normal — the thin volume creates false LVNs
- **Solution**: Flag early-close sessions; optionally skip or reduce confidence

### DST Handling
Use `zoneinfo.ZoneInfo("America/New_York")`. DST transitions create:
- Spring forward (March): one 23-hour session (one bar "missing" at 2 AM)
- Fall back (November): one 25-hour session (2 AM appears twice)
- **Common mistake**: Hardcoding UTC-5 — breaks twice a year
- **Solution**: `from zoneinfo import ZoneInfo; ET = ZoneInfo("America/New_York")` — handles automatically

## Continuous Contract Data

### NQ Data Observation
The NQ parquet shows prices of ~1402 in Dec 2008 and ~24,326 in March 2026. This is **back-adjusted continuous contract data** (additive adjustment). This means:
- Price levels from 2014 are comparable to 2026 on a relative basis
- ATR calculations are valid across the full history
- LVN price levels from prior sessions are comparable to current — no normalization needed for backtesting (the adjustment has already been applied)
- **Important**: Do NOT apply additional price normalization to the raw bars — the data provider already did it

### Front-Month Roll
The ES data has explicit `Symbol` column (ESH14, ESM14, etc.) showing contract rolls. The NQ data has continuous timestamps without explicit symbol tags. For backtesting purposes:
- Treat both as continuous price series (the adjustment handles discontinuities)
- Do NOT compute SMT correlation across a roll date — the price relationship is temporarily distorted
- **Solution**: Detect rolls by looking for Symbol changes in ES data; when a roll occurs, skip SMT for 1-2 sessions while correlation re-stabilizes

## Volume Profile Implementation Details

### Pre-Market Profile vs Intra-Session Development
**Strategy rule**: The SVP is built from 6 PM prior → current bar. This means:
- At 9:30 AM: profile covers 15.5 hours of overnight trading — already substantial
- During RTH: profile grows bar-by-bar (developing VP)
- **For backtesting M1**: Use the profile built from ALL bars prior to 9:30 AM as the "frozen" pre-RTH profile. Do NOT rebuild during RTH bars (avoids complexity and keeps LVN levels stable throughout the session)
- **Future M2 enhancement**: Use developing VP that updates every bar

### LVN Invalidation Timing
The consolidation filter (3 bars body overlap OR 4 midpoint crossings) runs on every RTH bar:
- When an LVN is invalidated, mark `valid=False` immediately
- Do NOT re-validate in the same session even if price moves away
- Check invalidation BEFORE checking entry conditions at each bar

### POC Calculation
POC = price level with maximum cumulative volume. With >15 hours of pre-market data, the POC is stable and meaningful by 9:30 AM.

## Single Print Detection

### The Overnight Respect Check
An SP zone is "respected overnight" if:
1. Price approached within 2 ticks of the zone boundary during 18:00–09:30 ET
2. At least one bar's WICK entered the zone (high > zone_low or low < zone_high)
3. But NO bar's BODY closed fully inside the zone (min(open,close) > zone_low AND max(open,close) < zone_high is VIOLATED — i.e., we need body to stay OUTSIDE)

**Edge case — zone at extremes**: If the SP zone is at the overnight high or low, "approached within 2 ticks" may be trivially satisfied. Add a check: the bar must be approaching FROM the outside (not already past the zone).

**Edge case — multiple tests**: Price can test the SP zone multiple times overnight. One clean rejection is sufficient; `respected_overnight = True` once set is never reverted.

### SP Zone as Target
Use SP zone boundaries as TP levels:
- **Long trade**: TP1 = `sp_zone.low` (bottom edge of SP zone ABOVE entry)
- **Short trade**: TP1 = `sp_zone.high` (top edge of SP zone BELOW entry)
- Rationale: price is expected to fill the print and stall there

## Swing Detection Anti-Lookahead Patterns

### The Confirmation Delay (Critical)
A swing high at bar `i` with `lookback=5` is **confirmed at bar `i+5`**. Code structure:

```python
# WRONG (lookahead):
if bars[i].high == max(bars[i-5:i+6]):  # i+6 includes future bars
    mark_swing_high(i)

# CORRECT:
if bars[i].high == max(bars[i-5:i+1]):  # only past + current
    if all(bars[j].high < bars[i].high for j in range(i+1, i+6)):
        # Only mark at bar i+5 when confirmed
        confirmed_at = i + lookback
        mark_swing_high(i, confirmed_at=confirmed_at)
```

### Using Swings in Signal Detection
At any bar `b`, only use swings where `confirmed_at <= b`. This ensures the swing was already "known" before the current bar. NEVER use a swing where `bar_index >= b` unless `confirmed_at <= b`.

## SMT-Specific Implementation

### Correlation Filter
Compute rolling Pearson correlation between NQ and ES bar returns:
```python
nq_returns = nq_close.pct_change()
es_returns = es_close.pct_change()
correlation = nq_returns.rolling(20).corr(es_returns)
```
Only generate SMT signals when `correlation >= 0.70` at the time of signal detection. Below 0.70, the instruments are in temporary divergence mode (e.g., sector rotation) and SMT is unreliable.

### SMT vs ISMT Priority and Weighting
Per project spec: ISMT is weighted slightly higher than SMT.
- In M1 (mechanical backtest): both signal types trigger identical trade logic. The "weight" distinction only matters for M2 ML features.
- In M2 feature engineering: add feature `signal_source` (ISMT=1, SMT=0) and `signal_strength` (ISMT sweep size / ISMT confidence score vs SMT divergence strength).
- At the entry check level: if both ISMT and SMT are present simultaneously, use ISMT as the authoritative signal.

### Null Guard on Prior Swings
The `get_prior_swing()` function must handle the case where no prior swing exists:
```python
if prior_swing is None:
    continue  # Cannot compute divergence without a reference point
```
This happens at session start (first 10-15 bars) — just skip, no signal possible.

## Execution Edge Cases

### Partial Exit Accounting
- At TP1: `exit_size_1 = floor(full_size * 0.60)` — use floor to get whole contracts
- At TP2: `exit_size_2 = remaining_size` (all remaining contracts)
- Commission: charge per side per exit event — TP1 and TP2 are separate exits, each charges 1 commission per contract
- Total commission for a winning trade: `full_size * commission * 2 (entry) + exit_size_1 * commission + exit_size_2 * commission`

### Zero-RR Guard
Before computing RR: `if abs(entry_price - stop_price) < tick_size: skip setup`
Before position size: `if risk_per_contract <= 0: skip setup`

### Gap Open Invalidation
At 9:30 AM, if price has already gapped through an LVN (open price on the first RTH bar is on the other side of the LVN from the prior close), that LVN is immediately invalidated. Check this before the session's first entry evaluation.
