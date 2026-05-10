from data_loader import load_csv
from indicators import add_indicators
from strategies import RSIMACDStrategy
import os


def run_strategy_demo():
    # We assume data/2330.TW.csv is fetched. For demo purposes we check if it exists
    filepath = "data/2330.TW.csv"
    if not os.path.exists(filepath):
        print(f"File {filepath} not found. Please run fetch_yf.py first.")
        return

    # Pipeline
    df = load_csv(filepath)
    df = add_indicators(df)

    # Strategy
    strategy = RSIMACDStrategy(rsi_col="rsi_14", macd_hist_col="macd_hist")
    signals = strategy.generate_signals(df)
    df["signal"] = signals

    print("--- Signals Generated ---")
    print(df[["close", "rsi_14", "macd_hist", "signal"]].tail(10))

    # Formal Backtest Engine
    from backtest import BacktestEngine
    from analytics import calculate_kpi

    engine = BacktestEngine(transaction_cost=0.001)
    df_bt = engine.run(df)

    kpi = calculate_kpi(df_bt)

    print("\n--- KPI ---")
    for k, v in kpi.items():
        print(f"{k}: {v:.4f}")


if __name__ == "__main__":
    run_strategy_demo()
