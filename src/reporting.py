"""
REPORT-02–05, D-12–D-14: incremental CSV, per-trade HTML under RunPaths, summary stub.

CSV columns are a superset of TradeResult / TradeSetup fields for downstream ML exports.
"""

from __future__ import annotations

import csv
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List

from plotly.graph_objects import Figure

from src.config import RunPaths
from src.position import TradeResult


def _trade_to_csv_row(trade: TradeResult) -> Dict[str, Any]:
    d = asdict(trade)
    d["exit_type"] = trade.exit_type.value
    return d


CSV_FIELDNAMES: List[str] = [
    "setup_id",
    "entry_price",
    "stop_price",
    "target_price",
    "tp2_price",
    "rr_ratio",
    "direction",
    "created_at",
    "setup_type",
    "lvn_id",
    "exit_price_tp1",
    "exit_price_tp2",
    "exit_type",
    "gross_pnl",
    "net_pnl",
    "total_commission",
    "trade_index",
    "session_date",
    "entry_bar_index",
    "exit_bar_index",
    "signal_source",
    "position_size_scale",
]


def chart_filename_d14(trade: TradeResult) -> str:
    """D-14: {trade_index:04d}_{session_date}_{direction}_{setup_type}.html"""
    stype = str(trade.setup_type).replace(" ", "_")
    return f"{trade.trade_index:04d}_{trade.session_date}_{trade.direction}_{stype}.html"


class RunWriter:
    """Append trades to CSV, write Plotly HTML, mirror rows for summary."""

    def __init__(self, paths: RunPaths, instrument_symbol: str = "NQ") -> None:
        self.paths = paths
        self.instrument_symbol = instrument_symbol
        self.rows: List[Dict[str, Any]] = []
        paths.run_root.mkdir(parents=True, exist_ok=True)
        paths.charts_dir.mkdir(parents=True, exist_ok=True)

    def append_trade_csv(self, trade: TradeResult) -> None:
        row = _trade_to_csv_row(trade)
        self.rows.append(row)
        path = self.paths.csv_path
        write_header = not path.exists()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES, extrasaction="ignore")
            if write_header:
                w.writeheader()
            w.writerow(
                {k: ("" if row.get(k) is None else row[k]) for k in CSV_FIELDNAMES}
            )

    def write_trade_html(self, trade: TradeResult, fig: Figure) -> Path:
        out = self.paths.charts_dir / chart_filename_d14(trade)
        fig.write_html(str(out), include_plotlyjs="cdn", full_html=True)
        return out

    def finalize_summary(self) -> Path:
        """REPORT-04: minimal Phase 5 stub — full metrics deferred to Phase 6."""
        total = sum(float(r.get("net_pnl", 0) or 0) for r in self.rows)
        csv_rel = self.paths.csv_path.name
        text = "\n".join(
            [
                "# Backtest run summary (Phase 5 stub — metrics in Phase 6)",
                "",
                f"- Run timestamp: `{self.paths.run_timestamp}`",
                f"- Instrument: `{self.instrument_symbol}`",
                f"- Trades recorded: {len(self.rows)}",
                f"- Total net PnL: ${total:.2f}",
                f"- CSV: `{csv_rel}` (under run root)",
                "",
            ]
        )
        out = self.paths.run_root / "summary.md"
        out.write_text(text, encoding="utf-8")
        return out
