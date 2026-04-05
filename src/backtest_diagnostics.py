"""
Counters and reports for why the backtest rarely or never fires trades.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class BacktestDiagnostics:
    """Aggregated during run_full_backtest when enabled."""

    blocker_counts: Counter[str] = field(default_factory=Counter)
    pre_entry_counts: Counter[str] = field(default_factory=Counter)
    sessions_total: int = 0
    sessions_neutral_bias: int = 0
    sessions_zero_valid_lvns: int = 0
    sessions_zero_lvn_candidates: int = 0
    rth_bars_total: int = 0
    rth_bars_with_valid_lvns: int = 0
    setups_built: int = 0
    trades_recorded: int = 0
    session_snapshots: List[Dict[str, Any]] = field(default_factory=list)
    max_session_snapshots: int = 500

    def record_blocker(self, code: str) -> None:
        if code:
            self.blocker_counts[code] += 1

    def record_pre_entry(self, code: str) -> None:
        if code:
            self.pre_entry_counts[code] += 1

    def maybe_snapshot_session(
        self,
        *,
        session_date: str,
        bias: str,
        n_lvn_candidates: int,
        n_valid_lvns: int,
        n_sp_zones: int,
        n_respected_sp: int,
        n_ismt: int,
        n_smt: int,
        confluence_history_sessions: int,
    ) -> None:
        if len(self.session_snapshots) >= self.max_session_snapshots:
            return
        self.session_snapshots.append(
            {
                "session_date": session_date,
                "bias": bias,
                "lvn_candidates": n_lvn_candidates,
                "valid_lvns_after_confluence": n_valid_lvns,
                "sp_zones_prior_session": n_sp_zones,
                "respected_sp": n_respected_sp,
                "ismt_signals_eod": n_ismt,
                "smt_signals_eod": n_smt,
                "confluence_history_len": confluence_history_sessions,
            }
        )

    def top_blockers(self, n: int = 15) -> List[tuple[str, int]]:
        return self.blocker_counts.most_common(n)

    def to_json_dict(self) -> Dict[str, Any]:
        return {
            "sessions_total": self.sessions_total,
            "sessions_neutral_bias": self.sessions_neutral_bias,
            "sessions_zero_lvn_candidates": self.sessions_zero_lvn_candidates,
            "sessions_zero_valid_lvns": self.sessions_zero_valid_lvns,
            "rth_bars_total": self.rth_bars_total,
            "rth_bars_with_valid_lvns": self.rth_bars_with_valid_lvns,
            "setups_built": self.setups_built,
            "trades_recorded": self.trades_recorded,
            "entry_blockers_top": [
                {"code": k, "count": v} for k, v in self.top_blockers(30)
            ],
            "pre_entry_rejections_top": [
                {"code": k, "count": v} for k, v in self.pre_entry_counts.most_common(30)
            ],
            "session_snapshots_sample": self.session_snapshots[:200],
        }

    def write_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_json_dict(), indent=2), encoding="utf-8")

    def print_summary(self) -> None:
        print("\n--- Backtest diagnostics (why no / few trades?) ---")
        print(
            f"Sessions: {self.sessions_total} | neutral bias: {self.sessions_neutral_bias} | "
            f"no LVN candidates: {self.sessions_zero_lvn_candidates} | "
            f"no valid LVNs (after confluence): {self.sessions_zero_valid_lvns}"
        )
        print(
            "Note: first session(s) often have zero valid LVNs until confluence history fills; "
            "3L_* / 3S_* = three-step long/short gate; AL_/AS_ = aggressive ledge."
        )
        print(
            f"RTH bars: {self.rth_bars_total} | RTH bars with ≥1 valid LVN: {self.rth_bars_with_valid_lvns}"
        )
        print(f"Setups passing ENTRY-05 validate: {self.setups_built} | trades logged: {self.trades_recorded}")
        if self.blocker_counts:
            print("Top entry-pattern blockers (counts across RTH bar × LVN × pattern):")
            for code, cnt in self.top_blockers(12):
                print(f"  {cnt:8d}  {code}")
        if self.pre_entry_counts:
            print("Pre-entry (validate_pre_entry) rejections:")
            for code, cnt in self.pre_entry_counts.most_common(12):
                print(f"  {cnt:8d}  {code}")
        print("--- end diagnostics ---\n")
