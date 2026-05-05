import numpy as np
import pandas as pd

def calculate_kpi(df: pd.DataFrame):
    if "equity" not in df.columns or "strategy_returns" not in df.columns:
        raise ValueError("DataFrame must contain 'equity' and 'strategy_returns' columns")
        
    equity = df["equity"]

    total_return = equity.iloc[-1] - 1

    returns = df["strategy_returns"].dropna()

    sharpe = np.sqrt(252) * returns.mean() / returns.std() if returns.std() != 0 else 0

    drawdown = equity / equity.cummax() - 1
    mdd = drawdown.min()

    return {
        "total_return": total_return,
        "sharpe": sharpe,
        "max_drawdown": mdd
    }
