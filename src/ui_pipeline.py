import datetime
import json
import os


from .analytics import calculate_kpi
from .backtest import BacktestEngine
from .indicators import add_indicators
from .market_data import fetch_market_data
from .strategy_registry import StrategyRegistry


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
    interval: str = "1d",
) -> dict:
    """
    Encapsulates the complete trading analysis pipeline.
    Ensures UI components don't interact directly with deep business logic.
    """
    market_result = fetch_market_data(symbol, period=period, interval=interval)
    df = market_result.dataframe

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
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data_source": market_result.source,
        "fallback_used": market_result.fallback_used,
        "data_warnings": market_result.warnings,
        "data_diagnostics": market_result.diagnostics,
        "data_freshness": market_result.data_freshness,
        "last_bar_time": market_result.last_bar_time,
        "is_stale": market_result.is_stale,
        "provider_name": market_result.provider_name,
        "attempted_sources": market_result.attempted_sources,
        "fetch_latency_ms": market_result.fetch_latency_ms,
        "cache_hit": market_result.cache_hit,
    }

    return {
        "df": df_bt,
        "kpi": kpi,
        "metadata": metadata,
    }
