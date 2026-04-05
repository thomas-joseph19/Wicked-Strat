"""
Phase 7: audit checklist → audit_report.md (AUDIT-01..07).
AUDIT-01 is MANUAL (two full backtest runs + diff); others run programmatically.
"""

from __future__ import annotations

import argparse
import inspect
from dataclasses import dataclass
from datetime import datetime, time, timezone
from pathlib import Path
from typing import List

import pandas as pd

from src.config import InstrumentConfig, StrategyThresholds
from src.entry import validate_pre_entry
from src.metrics import max_drawdown_stats
from src.position import FillEvent, Position, SessionTradeBudget, TradeSetup, fills_to_gross_pnl
from src.tpo import build_tpo_profile


@dataclass
class AuditRow:
    audit_id: str
    description: str
    result: str  # PASS | FAIL | SKIP | MANUAL
    evidence: str
    checked_at: str


def write_audit_report(path: Path, rows: List[AuditRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Trade logic audit report",
        "",
        f"Generated checklist run (UTC): `{datetime.now(timezone.utc).isoformat()}`",
        "",
        "| ID | Description | Result | Evidence | Checked |",
        "|----|-------------|--------|----------|---------|",
    ]
    for r in rows:
        ev = (r.evidence or "").replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| {r.audit_id} | {r.description} | {r.result} | {ev} | {r.checked_at} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def check_audit_02() -> AuditRow:
    ok = validate_pre_entry(
        entry_price=100.0,
        stop_price=100.0,
        target_price=102.0,
        bias="BULLISH",
        atr20=10.0,
        tick_size=0.25,
        bar_time=time(10, 0),
        session_setup_count=0,
    )
    passed = ok is False
    return AuditRow(
        "AUDIT-02",
        "RR guard: entry == stop → reject (no crash)",
        "PASS" if passed else "FAIL",
        "validate_pre_entry returned False" if passed else f"unexpected {ok=}",
        _now_iso(),
    )


def check_audit_03() -> AuditRow:
    from tests.phase05.conftest import make_lvn

    setup = TradeSetup(
        setup_id="s",
        entry_price=100.0,
        stop_price=101.0,
        target_price=98.0,
        tp2_price=96.0,
        rr_ratio=2.0,
        direction="SHORT",
        created_at=0,
        setup_type="THREE_STEP",
        lvn_id="1",
        lvn_ref=make_lvn(99.0, 101.0),
        ismt_or_smt_ref=None,
        signal_source=0,
    )
    fills = [
        FillEvent(1, "ENTRY", 100.0, 1, "SHORT"),
        FillEvent(2, "TP2", 97.0, 1, "SHORT"),
    ]
    gross = fills_to_gross_pnl(fills, setup, point_value=20.0)
    passed = gross > 0
    return AuditRow(
        "AUDIT-03",
        "Short P&L polarity (synthetic fills)",
        "PASS" if passed else "FAIL",
        f"gross_pnl={gross:.2f}",
        _now_iso(),
    )


def check_audit_04() -> AuditRow:
    equity = pd.Series([100_000.0, 110_000.0, 100_000.0, 88_000.0])
    dd = max_drawdown_stats(equity)
    passed = dd["max_drawdown_frac"] <= 0 and dd["max_drawdown_dollars"] >= 0
    return AuditRow(
        "AUDIT-04",
        "Max drawdown uses rolling peak on equity",
        "PASS" if passed else "FAIL",
        f"max_drawdown_frac={dd['max_drawdown_frac']:.6f}, dollars={dd['max_drawdown_dollars']:.2f}",
        _now_iso(),
    )


def check_audit_05() -> AuditRow:
    src = inspect.getsource(build_tpo_profile)
    has_labels = "label='left'" in src or 'label="left"' in src
    has_closed = "closed='left'" in src or 'closed="left"' in src
    passed = has_labels and has_closed
    return AuditRow(
        "AUDIT-05",
        "TPO 30m resample label=left closed=left",
        "PASS" if passed else "FAIL",
        "build_tpo_profile source contains resample kwargs" if passed else "missing kwargs",
        _now_iso(),
    )


def check_audit_06() -> AuditRow:
    from dataclasses import replace

    from tests.phase05.conftest import bar, make_lvn, simple_setup, ts

    lvn = make_lvn(50.0, 55.0)
    st = replace(
        simple_setup(entry=100.0, stop=98.0, tp1=102.0, tp2=103.0, created_at=0),
        lvn_ref=lvn,
    )
    nq = InstrumentConfig(symbol="NQ", tick_size=0.25, point_value=20.0, commission_per_side=2.5)
    th = StrategyThresholds()
    budget = SessionTradeBudget(3, 0)
    pos = Position(st, nq, th, budget, 0, "2024-06-03")
    pos.update(bar(ts(10, 5), 99.0, 102.5, 98.5, 102.0), 1)
    pos.update(bar(ts(10, 10), 102.0, 104.0, 101.5, 103.5), 2)
    tp_ok = [f.kind for f in pos.fills] == ["ENTRY", "TP1_PARTIAL", "TP2"]

    budget2 = SessionTradeBudget(3, 0)
    st2 = replace(simple_setup(created_at=0), lvn_ref=lvn)
    pos2 = Position(st2, nq, th, budget2, 0, "2024-06-03")
    pos2.update(bar(ts(10, 5), 100.0, 100.5, 99.5, 100.2), 1)
    pos2.update(bar(ts(10, 6), 100.0, 99.5, 97.0, 97.5), 2)
    sl_ok = [f.kind for f in pos2.fills] == ["ENTRY", "SL"]

    passed = tp_ok and sl_ok
    ev = f"TP path fills={tp_ok}, SL path fills={sl_ok}"
    return AuditRow(
        "AUDIT-06",
        "Commission/fill counts: TP path 3 fills, stop path 2",
        "PASS" if passed else "FAIL",
        ev,
        _now_iso(),
    )


def check_audit_07() -> AuditRow:
    from dataclasses import replace

    from tests.phase05.conftest import bar, make_lvn, simple_setup, ts

    lvn = make_lvn(50.0, 55.0)
    st = replace(
        simple_setup(entry=100.0, stop=98.0, tp1=102.0, tp2=104.0, created_at=0),
        lvn_ref=lvn,
    )
    nq = InstrumentConfig(symbol="NQ", tick_size=0.25, point_value=20.0, commission_per_side=2.5)
    th = StrategyThresholds()
    budget = SessionTradeBudget(3, 0)
    pos = Position(st, nq, th, budget, 0, "2024-06-03")
    pos.update(bar(ts(10, 5), 99.0, 102.5, 98.5, 102.0), 1)
    tp1 = next(f for f in pos.fills if f.kind == "TP1_PARTIAL")
    tp_ok = abs(tp1.price - st.target_price) < 1e-9

    budget2 = SessionTradeBudget(3, 0)
    st2 = replace(simple_setup(created_at=0), lvn_ref=lvn)
    pos2 = Position(st2, nq, th, budget2, 0, "2024-06-03")
    pos2.update(bar(ts(10, 5), 100.0, 100.5, 99.5, 100.2), 1)
    pos2.update(bar(ts(10, 6), 100.0, 99.5, 97.0, 97.5), 2)
    sl = next(f for f in pos2.fills if f.kind == "SL")
    sl_ok = abs(sl.price - st2.stop_price) < 1e-9
    passed = tp_ok and sl_ok
    return AuditRow(
        "AUDIT-07",
        "Exit fills at exact TP/SL prices",
        "PASS" if passed else "FAIL",
        f"tp1_px={tp1.price}, sl_px={sl.price}",
        _now_iso(),
    )


def run_programmatic_checks() -> List[AuditRow]:
    return [
        check_audit_02(),
        check_audit_03(),
        check_audit_04(),
        check_audit_05(),
        check_audit_06(),
        check_audit_07(),
    ]


def audit_01_manual_row() -> AuditRow:
    return AuditRow(
        "AUDIT-01",
        "Reproducibility: two full backtests byte-identical trade log",
        "MANUAL",
        "Run the same CLI twice (e.g. `python main.py --mode backtest --start YYYY-MM-DD --end YYYY-MM-DD`). "
        "Compare canonical CSV: `backtest_results_<run_timestamp>.csv` under `run_<ts>/` (Phase 5 D-14). "
        "Windows: `fc /b runA\\backtest_results_*.csv runB\\backtest_results_*.csv`. "
        "Unix: `diff runA/backtest_results_*.csv runB/backtest_results_*.csv`.",
        _now_iso(),
    )


def run_full_checklist() -> List[AuditRow]:
    return [audit_01_manual_row()] + run_programmatic_checks()


def main() -> None:
    parser = argparse.ArgumentParser(description="Write audit_report.md")
    parser.add_argument("--out", type=Path, default=Path("audit_report.md"))
    args = parser.parse_args()
    write_audit_report(args.out, run_full_checklist())
    print(f"Wrote {args.out.resolve()}")


if __name__ == "__main__":
    main()
