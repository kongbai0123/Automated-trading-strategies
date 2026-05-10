import pandas as pd


def calculate_sma(series: pd.Series, period: int) -> pd.Series:
    """Calculate Simple Moving Average."""
    return series.rolling(window=period).mean()


def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    """Calculate Exponential Moving Average."""
    return series.ewm(span=period, adjust=False).mean()


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    alpha = 1 / period
    avg_gain = gain.ewm(alpha=alpha, adjust=False).mean()
    avg_loss = loss.ewm(alpha=alpha, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    # Handle division by zero when average loss is 0
    rsi.loc[avg_loss == 0] = 100

    return rsi


def calculate_macd(
    series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> pd.DataFrame:
    """Calculate MACD (Moving Average Convergence Divergence)."""
    ema_fast = calculate_ema(series, fast)
    ema_slow = calculate_ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal)
    histogram = macd_line - signal_line

    return pd.DataFrame(
        {"MACD": macd_line, "Signal": signal_line, "Histogram": histogram}
    )


def calculate_atr(
    high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
) -> pd.Series:
    """Calculate Average True Range."""
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


def calculate_bollinger_bands(
    series: pd.Series, period: int = 20, std_dev: float = 2.0
) -> pd.DataFrame:
    """Calculate Bollinger Bands."""
    sma = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    upper_band = sma + (std * std_dev)
    lower_band = sma - (std * std_dev)
    return pd.DataFrame(
        {"BB_Middle": sma, "BB_Upper": upper_band, "BB_Lower": lower_band}
    )


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    out["sma_20"] = calculate_sma(out["close"], 20)
    out["sma_50"] = calculate_sma(out["close"], 50)
    out["ema_20"] = calculate_ema(out["close"], 20)
    out["rsi_14"] = calculate_rsi(out["close"], 14)

    macd_df = calculate_macd(out["close"])
    out["macd"] = macd_df["MACD"]
    out["macd_signal"] = macd_df["Signal"]
    out["macd_hist"] = macd_df["Histogram"]

    out["atr_14"] = calculate_atr(out["high"], out["low"], out["close"])

    bb_df = calculate_bollinger_bands(out["close"])
    out["bb_upper"] = bb_df["BB_Upper"]
    out["bb_middle"] = bb_df["BB_Middle"]
    out["bb_lower"] = bb_df["BB_Lower"]

    return out
