import polars as pl
import numpy as np
from datetime import datetime

class BacktestSimulator:
    """
    Simulates trade execution (TP/SL) for generated signals without hindsight (Req 5.1).
    """

    def __init__(self, data: pl.DataFrame):
        self.data_map = data.to_dicts()

    def run_simulation(self, signals: list[dict]) -> list[dict]:
        """
        Processes each signal chronologically.
        """
        results = []
        data_len = len(self.data_map)
        data_ptr = 0
        
        for signal in signals:
            while data_ptr < data_len and self.data_map[data_ptr]["timestamp"] < signal["timestamp"]:
                data_ptr += 1
                
            if data_ptr >= data_len:
                break
                
            entry_ptr = data_ptr + 1
            if entry_ptr >= data_len:
                continue
                
            entry_price = self.data_map[entry_ptr]["open"]
            stop = signal["stop"]
            target = signal["target"]
            direction = signal["direction"]
            
            outcome = None
            exit_price = None
            exit_time = None
            
            for j in range(entry_ptr, data_len):
                high = self.data_map[j]["high"]
                low = self.data_map[j]["low"]
                
                if direction == "Long":
                    if low <= stop:
                        outcome = "LOSS"
                        exit_price = stop
                        exit_time = self.data_map[j]["timestamp"]
                        break
                    elif high >= target:
                        outcome = "WIN"
                        exit_price = target
                        exit_time = self.data_map[j]["timestamp"]
                        break
                else: # Short
                    if high >= stop:
                        outcome = "LOSS"
                        exit_price = stop
                        exit_time = self.data_map[j]["timestamp"]
                        break
                    elif low <= target:
                        outcome = "WIN"
                        exit_price = target
                        exit_time = self.data_map[j]["timestamp"]
                        break
            
            if outcome:
                # Points basis PnL
                if direction == "Long":
                    pnl = exit_price - entry_price
                else:
                    pnl = entry_price - exit_price
                    
                results.append({
                    **signal,
                    "actual_entry": entry_price,
                    "outcome": outcome,
                    "pnl": pnl,
                    "exit_time": exit_time
                })
                
        return results

class MetricsEngine:
    """
    Calculates final backtest statistics.
    """
    
    @staticmethod
    def calculate(results: list[dict]) -> dict:
        if not results:
            return {}
            
        pnls = [r["pnl"] for r in results]
        outcomes = [r["outcome"] for r in results]
        
        total_pnl = sum(pnls)
        wins = outcomes.count("WIN")
        losses = outcomes.count("LOSS")
        win_rate = wins / (wins + losses) if (wins + losses) > 0 else 0
        
        # Max Drawdown (cumulative points)
        cum_pnl = np.cumsum(pnls)
        running_max = np.maximum.accumulate(cum_pnl)
        drawdown_curve = running_max - cum_pnl
        max_dd = np.max(drawdown_curve) if len(drawdown_curve) > 0 else 0
        
        gross_profit = sum([p for p in pnls if p > 0])
        gross_loss = abs(sum([p for p in pnls if p < 0]))
        profit_factor = gross_profit / gross_loss if gross_loss != 0 else float('inf')
        
        return {
            "total_trades": len(results),
            "wins": wins,
            "losses": losses,
            "win_rate": f"{win_rate:.2%}",
            "total_pnl_points": round(total_pnl, 2),
            "max_drawdown_points": round(max_dd, 2),
            "profit_factor": round(profit_factor, 2)
        }

if __name__ == "__main__":
    # Corrected smoke test
    mock_data = pl.DataFrame({
        "timestamp": [datetime(2024, 1, 1, 9, i) for i in range(10)],
        "open": [1400.0] * 10,
        "high": [1400.5, 1400.5, 1402.0, 1403.0, 1404.0, 1405.0, 1406.0, 1402.0, 1400.0, 1396.0],
        "low":  [1399.5, 1399.5, 1400.5, 1401.5, 1402.5, 1403.5, 1404.5, 1400.5, 1398.5, 1394.5],
        "close": [1400.0] * 10
    })
    
    mock_signals = [
        {"timestamp": mock_data["timestamp"][0], "direction": "Long", "stop": 1398.0, "target": 1405.0} # WIN at index 5
    ]
    
    sim = BacktestSimulator(mock_data)
    results = sim.run_simulation(mock_signals)
    
    engine = MetricsEngine()
    metrics = engine.calculate(results)
    print(f"Outcome: {results[0]['outcome']}")
    print(f"Metrics: {metrics}")
