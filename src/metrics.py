"""
Phase 6: Institutional metrics (METRIC-01..06) — daily P&L, equity, drawdown, risk ratios.
"""

from __future__ import annotations

import math
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd

from src.config import RunPaths
from src.position import TradeResult


def build_daily_pnl_and_returns(
    trades: Sequence[TradeResult],
    account_size: float,
    zero_pnl_dates: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    METRIC-01 / D-01: Sum net_pnl by session_date; daily_return = daily_net_pnl / account_size.
    D-03: Optional zero_pnl_dates force rows with 0 P&L for Sharpe denominator integrity.
    """
    by_date: Dict[str, float] = {}
    for t in trades:
        by_date[t.session_date] = by_date.get(t.session_date, 0.0) + float(t.net_pnl)

    all_dates = sorted(set(by_date.keys()) | set(zero_pnl_dates or []))
    rows = []
    for d in all_dates:
        pnl = by_date.get(d, 0.0)
        rows.append(
            {
                "date": d,
                "daily_net_pnl": pnl,
                "daily_return": pnl / account_size if account_size else 0.0,
            }
        )
    return pd.DataFrame(rows)


def compounded_equity_from_returns(
    daily_returns: Union[pd.Series, Sequence[float]],
    start_equity: float = 100_000.0,
) -> pd.Series:
    """D-04: E[0]=start_equity, E[i]=E[i-1]*(1+r[i])."""
    r = pd.Series(daily_returns, dtype=float)
    eq = np.empty(len(r), dtype=float)
    cur = float(start_equity)
    for i in range(len(r)):
        cur *= 1.0 + float(r.iloc[i])
        eq[i] = cur
    return pd.Series(eq, index=r.index)


def max_drawdown_stats(equity: pd.Series) -> Dict[str, Any]:
    """METRIC-04 / P8: rolling peak; dd = (equity - peak) / peak."""
    vals = equity.astype(float).values
    if len(vals) == 0:
        return {"max_drawdown_frac": 0.0, "max_drawdown_dollars": 0.0, "peak_idx": 0, "trough_idx": 0}
    peak_running = np.maximum.accumulate(vals)
    dd = (vals - peak_running) / peak_running
    trough_i = int(np.argmin(dd))
    mdd_frac = float(dd[trough_i])
    peak_i = int(np.argmax(vals[: trough_i + 1]))
    peak_at_trough = float(peak_running[trough_i])
    trough_val = float(vals[trough_i])
    return {
        "max_drawdown_frac": mdd_frac,
        "max_drawdown_dollars": peak_at_trough - trough_val,
        "peak_idx": peak_i,
        "trough_idx": trough_i,
    }


def profit_factor(trades: Sequence[TradeResult]) -> float:
    """
    METRIC-05 / C8: gross_wins / abs(gross_losses); no losers -> gross_wins; none/all zero -> 0.
    """
    gross_wins = sum(float(t.net_pnl) for t in trades if t.net_pnl > 0)
    gross_losses = sum(float(t.net_pnl) for t in trades if t.net_pnl < 0)
    if not trades:
        return 0.0
    if gross_losses == 0:
        if gross_wins > 0:
            return float(gross_wins)
        return 0.0
    return gross_wins / abs(gross_losses)


def basic_trade_stats(trades: Sequence[TradeResult]) -> Dict[str, Any]:
    """
    METRIC-06: win if net_pnl>0, loss if <0; zeros excluded from avg_win/avg_loss denominators.
    """
    total = len(trades)
    wins = [float(t.net_pnl) for t in trades if t.net_pnl > 0]
    losses = [float(t.net_pnl) for t in trades if t.net_pnl < 0]
    total_net = sum(float(t.net_pnl) for t in trades)
    win_rate = len(wins) / total if total else 0.0
    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = sum(losses) / len(losses) if losses else 0.0
    return {
        "total_trades": total,
        "win_rate": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "total_net_pnl": total_net,
    }


def sharpe_ratio_annualized(
    daily_returns: pd.Series,
    trading_days_per_year: int = 252,
) -> Optional[float]:
    """METRIC-02 / D-06: sample std ddof=1; None if len<2 or std==0."""
    s = pd.Series(daily_returns, dtype=float).dropna()
    if len(s) < 2:
        return None
    std = float(s.std(ddof=1))
    if std == 0.0 or math.isnan(std):
        return None
    return float(s.mean() / std) * math.sqrt(trading_days_per_year)


def sortino_ratio_annualized(
    daily_returns: pd.Series,
    trading_days_per_year: int = 252,
) -> Tuple[Optional[float], bool]:
    """
    METRIC-03 / D-07: downside r<0 only; downside_variance = mean(r^2); ann denominator * sqrt(252).
    Returns (ratio_or_None, downside_empty).
    """
    s = pd.Series(daily_returns, dtype=float).dropna()
    downside = s[s < 0]
    if downside.empty:
        return None, True
    downside_var = float((downside**2).mean())
    downside_dev_daily = math.sqrt(downside_var)
    if downside_dev_daily == 0.0:
        return None, True
    denom = downside_dev_daily * math.sqrt(trading_days_per_year)
    numer = float(s.mean()) * trading_days_per_year
    return numer / denom, False


def calmar_ratio(
    total_return_frac: float,
    num_years: float,
    max_drawdown_frac: float,
) -> Optional[float]:
    """D-08: annualized_return / abs(max_dd); num_years min 1/252."""
    ny = max(num_years, 1.0 / 252.0)
    if max_drawdown_frac == 0.0:
        return None
    ann = (1.0 + total_return_frac) ** (1.0 / ny) - 1.0
    return ann / abs(max_drawdown_frac)


def recovery_factor(total_net_pnl: float, max_drawdown_dollars: float) -> float:
    if max_drawdown_dollars == 0.0:
        return 0.0
    return float(total_net_pnl) / abs(float(max_drawdown_dollars))


def annual_breakdown(daily_df: pd.DataFrame) -> pd.DataFrame:
    """Per-calendar-year net PnL and Sharpe on that year's daily returns only."""
    if daily_df.empty:
        return pd.DataFrame(columns=["year", "net_pnl", "sharpe"])
    df = daily_df.copy()
    df["year"] = pd.to_datetime(df["date"]).dt.year
    rows = []
    for y, g in df.groupby("year"):
        rets = g["daily_return"]
        sh = sharpe_ratio_annualized(rets, 252)
        rows.append(
            {
                "year": int(y),
                "net_pnl": float(g["daily_net_pnl"].sum()),
                "sharpe": sh,
            }
        )
    return pd.DataFrame(rows)


def _parse_iso(d: str) -> date:
    return datetime.strptime(d, "%Y-%m-%d").date()


def list_drawdown_episodes(
    dates: Sequence[str],
    equity: pd.Series,
    min_depth_frac: float = 0.05,
    max_rows: int = 10,
) -> List[Dict[str, Any]]:
    """
    Significant drawdowns vs running peak: peak -> trough -> recovery (equity > prior peak).
    depth_frac negative; duration in calendar days from peak to recovery or last date.
    """
    if len(dates) != len(equity):
        raise ValueError("dates and equity must have same length")
    n = len(equity)
    eq = equity.astype(float).values
    dts = [_parse_iso(str(d)) for d in dates]

    episodes: List[Dict[str, Any]] = []
    peak_eq = eq[0]
    peak_dt = dts[0]
    trough_eq = eq[0]
    trough_dt = dts[0]

    for i in range(1, n):
        e = eq[i]
        dt = dts[i]
        if e > peak_eq:
            if trough_eq < peak_eq:
                depth_frac = (trough_eq - peak_eq) / peak_eq
                if abs(depth_frac) >= min_depth_frac - 1e-12:
                    depth_dollars = float(peak_eq - trough_eq)
                    rec_dt: Optional[date] = dt
                    dur = (rec_dt - peak_dt).days
                    episodes.append(
                        {
                            "peak_date": peak_dt.isoformat(),
                            "trough_date": trough_dt.isoformat(),
                            "recovery_date": rec_dt.isoformat(),
                            "depth_frac": float(depth_frac),
                            "depth_dollars": depth_dollars,
                            "duration_calendar_days": dur,
                        }
                    )
            peak_eq = e
            peak_dt = dt
            trough_eq = e
            trough_dt = dt
        else:
            if e < trough_eq:
                trough_eq = e
                trough_dt = dt

    if trough_eq < peak_eq:
        depth_frac = (trough_eq - peak_eq) / peak_eq
        if abs(depth_frac) >= min_depth_frac - 1e-12:
            depth_dollars = float(peak_eq - trough_eq)
            episodes.append(
                {
                    "peak_date": peak_dt.isoformat(),
                    "trough_date": trough_dt.isoformat(),
                    "recovery_date": None,
                    "depth_frac": float(depth_frac),
                    "depth_dollars": depth_dollars,
                    "duration_calendar_days": (dts[-1] - peak_dt).days,
                }
            )

    episodes.sort(key=lambda x: x["depth_frac"])
    return episodes[:max_rows]


def _num_years_from_dates(dates: Sequence[str]) -> float:
    if not dates:
        return 1.0 / 252.0
    d0 = _parse_iso(str(sorted(dates)[0]))
    d1 = _parse_iso(str(sorted(dates)[-1]))
    days = max((d1 - d0).days, 1)
    return max(days / 365.25, 1.0 / 252.0)


def compute_and_write_institutional_summaries(
    trades: List[TradeResult],
    paths: RunPaths,
    account_size: float,
    config_yaml_text: str,
    instrument_symbol: str,
    run_timestamp: str,
    zero_pnl_dates: Optional[List[str]] = None,
    session_diag: Optional[Dict[str, Any]] = None,
    config_path: str = "config.yaml",
) -> None:
    """Compose metrics + summary.md + summary.json under paths.run_root."""
    from src.summary_report import build_summary_dict, build_summary_markdown, write_run_summaries

    daily_df = build_daily_pnl_and_returns(trades, account_size, zero_pnl_dates)
    rets = daily_df["daily_return"] if not daily_df.empty else pd.Series(dtype=float)
    if len(rets) == 0:
        equity = pd.Series([float(account_size)])
        dd = {"max_drawdown_frac": 0.0, "max_drawdown_dollars": 0.0, "peak_idx": 0, "trough_idx": 0}
    else:
        equity = compounded_equity_from_returns(rets, account_size)
        dd = max_drawdown_stats(equity)
    total_return_frac = float(equity.iloc[-1] / account_size - 1.0) if len(equity) else 0.0
    ny = _num_years_from_dates(daily_df["date"].tolist()) if len(daily_df) else 1.0 / 252.0
    calmar = calmar_ratio(total_return_frac, ny, dd["max_drawdown_frac"])
    sortino_val, sortino_empty = sortino_ratio_annualized(rets) if len(rets) else (None, True)
    stats = basic_trade_stats(trades)
    pf = profit_factor(trades)
    total_net = stats["total_net_pnl"]
    rec = recovery_factor(total_net, dd["max_drawdown_dollars"])
    sharpe = sharpe_ratio_annualized(rets) if len(rets) else None
    annual = annual_breakdown(daily_df)
    dates_list = daily_df["date"].tolist() if len(daily_df) else []
    episodes = list_drawdown_episodes(dates_list, equity, 0.05, 10) if len(dates_list) else []

    risk_stats = {
        "sharpe": sharpe,
        "sortino": sortino_val,
        "sortino_downside_empty": sortino_empty,
        "calmar": calmar,
        "max_drawdown_frac": dd["max_drawdown_frac"],
        "max_drawdown_dollars": dd["max_drawdown_dollars"],
        "recovery_factor": rec,
        "total_return_frac": total_return_frac,
        "cagr_approx": ((1 + total_return_frac) ** (1 / ny) - 1) if ny > 0 else None,
    }
    equity_stats = {**dd, "final_equity": float(equity.iloc[-1]) if len(equity) else account_size}

    # daily distribution
    if len(rets) >= 2:
        skew = float(pd.Series(rets).skew())
        kurt = float(pd.Series(rets).kurtosis())
    else:
        skew = 0.0
        kurt = 0.0
    daily_dist = {
        "trading_days": len(daily_df),
        "days_with_trades": int((daily_df["daily_net_pnl"] != 0).sum()) if len(daily_df) else 0,
        "std_daily_return": float(rets.std(ddof=1)) if len(rets) > 1 else 0.0,
        "skewness": skew,
        "kurtosis": kurt,
        "best_day_pnl": float(daily_df["daily_net_pnl"].max()) if len(daily_df) else 0.0,
        "worst_day_pnl": float(daily_df["daily_net_pnl"].min()) if len(daily_df) else 0.0,
    }

    run_meta = {
        "run_timestamp": run_timestamp,
        "instrument": instrument_symbol,
        "config_path": config_path,
        "trade_count": len(trades),
    }

    payload = build_summary_dict(
        trades=trades,
        daily_df=daily_df,
        equity_stats=equity_stats,
        risk_stats=risk_stats,
        trade_stats_extra={**stats, "profit_factor": pf},
        daily_distribution=daily_dist,
        annual_df=annual,
        drawdown_episodes=episodes,
        session_diag=session_diag or {},
        run_meta=run_meta,
        config_yaml_text=config_yaml_text,
        warnings=[],
    )
    md = build_summary_markdown(payload)
    write_run_summaries(paths.run_root, md, payload)

    from src.metrics_dashboard import build_metrics_dashboard_figure, write_metrics_dashboard_html

    dash_fig = build_metrics_dashboard_figure(payload, trades, account_size=account_size)
    write_metrics_dashboard_html(paths.run_root, run_timestamp, dash_fig)
