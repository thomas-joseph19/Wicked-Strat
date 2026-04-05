# SUMMARY.md — Research Synthesis

## Stack

**Core:** Python 3.9+, pandas 2.x + pyarrow, numpy 1.26+, zoneinfo (stdlib)
**Charts:** plotly 5.x (standalone HTML per trade + interactive dashboard)
**ML (M2):** xgboost 2.x + optuna 3.x
**Market calendar:** pandas_market_calendars (CME calendar for holidays/early closes)

**Key decisions:** Bar-by-bar session iteration (not vectorized) — lookahead-free by design. Session-scoped state reset. Pre-computed session profiles (frozen at 9:30 AM).

## Table Stakes

All of the following are required for a valid backtest (non-negotiable):

| Feature | Status |
|---------|--------|
| 24h Globex session boundary (6PM→6PM ET) | Required |
| Hindsight-free swing detection (confirmed_at delay) | Critical |
| LVN multi-session confluence filter | Required |
| LVN real-time consolidation invalidation | Required |
| Overnight SP zone respect check | Required |
| TPO bias pre-computation (before 9:30 AM) | Required |
| ISMT detection (single-instrument) | Required |
| SMT detection (dual-instrument, corr≥0.70) | Required |
| Full partial exit (60%/40%) | Required |
| Hard stop on LVN body close | Required |
| EOD force-close at 3:45 PM ET | Required |
| Reproducibility gate (2x identical runs) | Required |
| Per-trade Plotly HTML charts | Required |
| Output → D:\Algorithms\Wicked Backtest Results | Required |

## Watch Out For

**Top 5 risks ranked by severity:**

1. **Symmetric swing detection** (P2) — most common lookahead bias in practice; kills backtest validity silently
2. **Short trade P&L polarity** (P4) — can make a losing strategy appear profitable
3. **LVN carry-over across sessions** (P5) — entries at phantom levels; shows as profitable due to hindsight bias
4. **SMT signals on synthetic bars** (P7) — inflates signal frequency artificially
5. **DST timezone shifts** (C1) — session windows off by 1 hour twice a year; hard to detect without explicit testing

**Implementation priorities from research:**
- Use `zoneinfo` exclusively for all timestamp operations
- Separate `detected_at` from `confirmed_at` for every swing
- Mark synthetic forward-fill bars and gate all SMT computation on `not is_synthetic`
- Freeze SVP profile at 9:30 AM — do not rebuild during RTH
- Commission model: entry + each partial exit = multiple commission events
- For M2: note additive back-adjustment on NQ means price levels are consistent across the 12-year dataset — no additional normalization needed for M1, but MC engine must still do session-level offset normalization when stitching random chunks

## Architecture Recommendation

**Session-iterator pattern:**
```
for session in sessions:
    pre_rth_bars = session.bars_before_930()
    profile = build_svp(pre_rth_bars)
    lvns = detect_and_filter_lvns(profile, prior_sessions)
    bias = compute_tpo_bias(session.bars_30min_before_930())
    if bias == 'NEUTRAL': continue
    sp_zones = detect_and_filter_sp_zones(profile, pre_rth_bars)
    for bar in session.rth_bars():
        # stateful bar-by-bar loop
        update_lvn_validity(lvns, bar)
        check_entry_conditions(bar, lvns, sp_zones, bias, ...)
        update_open_positions(bar)
```

This pattern makes lookahead bias structurally impossible — the profile and zones are computed before the execution loop begins.
