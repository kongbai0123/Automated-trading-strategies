import pandas as pd
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))
from strategies import RSIMACDStrategy, MACrossoverStrategy


def test_rsi_macd_strategy():
    # Mock dataframe with rsi_14 and macd_hist
    df = pd.DataFrame({"rsi_14": [50, 25, 80, 50], "macd_hist": [0, 1, -1, 1]})

    strategy = RSIMACDStrategy(rsi_col="rsi_14", macd_hist_col="macd_hist")
    signals = strategy.generate_signals(df)

    assert signals[0] == 0  # Neutral
    assert signals[1] == 1  # RSI < 30 and MACD_Hist > 0 -> Buy
    assert signals[2] == -1  # RSI > 70 and MACD_Hist < 0 -> Sell
    assert signals[3] == 0  # RSI = 50, Neutral


def test_ma_crossover_strategy():
    # Mock dataframe with Short and Long MA
    df = pd.DataFrame({"sma_20": [10, 12, 14, 13, 11], "sma_50": [11, 11, 11, 14, 15]})

    strategy = MACrossoverStrategy(short_col="sma_20", long_col="sma_50")
    signals = strategy.generate_signals(df)

    assert signals[0] == 0  # Initial state
    assert (
        signals[1] == 1
    )  # Short(12) crosses above Long(11) from Short(10) <= Long(11) -> Buy
    assert signals[2] == 0  # Short(14) > Long(11) but no cross
    assert (
        signals[3] == -1
    )  # Short(13) crosses below Long(14) from Short(14) >= Long(11) -> Sell
    assert signals[4] == 0  # Continued down trend
