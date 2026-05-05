import pandas as pd
import json
import os
from .data_loader import load_csv, fetch_live_data
from .indicators import add_indicators
from .strategy_registry import StrategyRegistry
from .backtest import BacktestEngine
from .analytics import calculate_kpi
import datetime

def load_config() -> dict:
    config_path = "configs/ui_config.json"
    if not os.path.exists(config_path):
        return {}
    with open(config_path, "r") as f:
        return json.load(f)

def run_backtest_pipeline(
    symbol: str, 
    strategy_name: str, 
    strategy_params: dict, 
    transaction_cost: float,
    period: str = "2y",
    interval: str = "1d"
) -> dict:
    """
    Encapsulates the complete trading analysis pipeline.
    Ensures UI components don't interact directly with deep business logic.
    """
    # 1. Fetch live data
    try:
        df = fetch_live_data(symbol, period=period, interval=interval)
    except Exception as e:
        raise ValueError(f"Failed to fetch data for {symbol}: {e}")

    if df.empty:
        raise ValueError("Loaded dataset is empty.")

    # 2. Compute indicators
    try:
        df = add_indicators(df)
    except Exception as e:
        raise ValueError(f"Failed to compute indicators: {e}")

    # 3. Initialize Strategy & Generate Signals
    strategy = StrategyRegistry.get_strategy(strategy_name, **strategy_params)
    try:
        signals = strategy.generate_signals(df)
        df["signal"] = signals
    except Exception as e:
        raise ValueError(f"Strategy {strategy_name} failed: {e}")

    # 4. Backtesting
    engine = BacktestEngine(transaction_cost=transaction_cost)
    try:
        df_bt = engine.run(df)
    except Exception as e:
        raise ValueError(f"Backtest Engine failed: {e}")

    # 5. Calculate KPI
    kpi = calculate_kpi(df_bt)

    metadata = {
        "symbol": symbol,
        "strategy_name": strategy_name,
        "parameters": strategy_params,
        "transaction_cost": transaction_cost,
        "interval": interval,
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    return {
        "df": df_bt,
        "kpi": kpi,
        "metadata": metadata
    }
