from abc import ABC, abstractmethod

import pandas as pd


class Strategy(ABC):
    """Abstract base class for all trading strategies."""

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """
        Generate trading signals based on provided dataframe.
        Must return a Pandas Series with 1 (Buy), -1 (Sell), and 0 (Hold).
        """
        pass


class RSIMACDStrategy(Strategy):
    """
    Example Strategy combining RSI and MACD.
    Buy: RSI < 30 and MACD Histogram > 0
    Sell: RSI > 70 and MACD Histogram < 0
    """

    def __init__(self, rsi_col="rsi_14", macd_hist_col="macd_hist", overbought=70, oversold=30):
        self.rsi_col = rsi_col
        self.macd_hist_col = macd_hist_col
        self.overbought = overbought
        self.oversold = oversold

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        if self.rsi_col not in df.columns or self.macd_hist_col not in df.columns:
            raise ValueError(f"Required columns missing: {self.rsi_col}, {self.macd_hist_col}")

        signals = pd.Series(0, index=df.index)

        buy_cond = (df[self.rsi_col] < self.oversold) & (df[self.macd_hist_col] > 0)
        sell_cond = (df[self.rsi_col] > self.overbought) & (df[self.macd_hist_col] < 0)

        signals.loc[buy_cond] = 1
        signals.loc[sell_cond] = -1

        return signals


class MACrossoverStrategy(Strategy):
    """
    Moving Average Crossover Strategy.
    Buy: Short MA crosses above Long MA
    Sell: Short MA crosses below Long MA
    """

    def __init__(self, short_col="sma_20", long_col="sma_50"):
        self.short_col = short_col
        self.long_col = long_col

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        if self.short_col not in df.columns or self.long_col not in df.columns:
            raise ValueError(f"Required columns missing: {self.short_col}, {self.long_col}")

        signals = pd.Series(0, index=df.index)

        prev_short = df[self.short_col].shift(1)
        prev_long = df[self.long_col].shift(1)
        curr_short = df[self.short_col]
        curr_long = df[self.long_col]

        buy_cond = (prev_short <= prev_long) & (curr_short > curr_long)
        sell_cond = (prev_short >= prev_long) & (curr_short < curr_long)

        signals.loc[buy_cond] = 1
        signals.loc[sell_cond] = -1

        return signals


class BollingerBreakoutStrategy(Strategy):
    """
    Bollinger Bands Breakout Strategy.
    Buy: Close price crosses above Upper Band.
    Sell: Close price crosses below Lower Band.
    """

    def __init__(self, close_col="close", upper_col="bb_upper", lower_col="bb_lower"):
        self.close_col = close_col
        self.upper_col = upper_col
        self.lower_col = lower_col

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        if (
            self.close_col not in df.columns
            or self.upper_col not in df.columns
            or self.lower_col not in df.columns
        ):
            raise ValueError("Required columns missing for Bollinger Strategy.")

        signals = pd.Series(0, index=df.index)

        prev_close = df[self.close_col].shift(1)
        prev_upper = df[self.upper_col].shift(1)
        prev_lower = df[self.lower_col].shift(1)
        curr_close = df[self.close_col]
        curr_upper = df[self.upper_col]
        curr_lower = df[self.lower_col]

        # Breakout above upper band
        buy_cond = (prev_close <= prev_upper) & (curr_close > curr_upper)
        # Breakdown below lower band
        sell_cond = (prev_close >= prev_lower) & (curr_close < curr_lower)

        signals.loc[buy_cond] = 1
        signals.loc[sell_cond] = -1

        return signals
