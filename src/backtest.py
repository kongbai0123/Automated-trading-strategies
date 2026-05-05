import pandas as pd

class BacktestEngine:
    """
    Vectorized Backtesting Engine
    """
    def __init__(self, transaction_cost=0.001):
        self.transaction_cost = transaction_cost

    def run(self, df: pd.DataFrame, signal_col: str = "signal") -> pd.DataFrame:
        if signal_col not in df.columns:
            raise ValueError(f"Missing signal column: {signal_col}")

        out = df.copy()

        # Position (持倉)
        import numpy as np
        out["position"] = out[signal_col].replace(0, np.nan).ffill().fillna(0)

        # Return
        out["returns"] = out["close"].pct_change()

        # Strategy return（t+1執行）
        out["strategy_returns"] = out["position"].shift(1) * out["returns"]

        # Transaction cost
        trades = out["position"].diff().abs()
        out["cost"] = trades * self.transaction_cost

        out["strategy_returns"] = out["strategy_returns"] - out["cost"]

        # Equity curve
        out["equity"] = (1 + out["strategy_returns"]).cumprod()

        return out
