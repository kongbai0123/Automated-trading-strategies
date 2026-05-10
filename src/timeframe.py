import pandas as pd


def resample_ohlcv(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """
    Resample OHLCV data to a higher timeframe.
    timeframe: '1mo', '1wk', '1d', '60m', '30m', '15m', '5m', '1m'
    """
    if df.empty:
        return df

    # Map timeframe to pandas frequency
    tf_map = {
        "1mo": "M",
        "1wk": "W",
        "1d": "D",
        "60m": "60min",
        "30m": "30min",
        "15m": "15min",
        "5m": "5min",
        "1m": "1min",
    }

    freq = tf_map.get(timeframe)
    if not freq:
        return df  # Return original if not found or no resampling needed

    # Ensure index is datetime
    if not isinstance(df.index, pd.DatetimeIndex):
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])
            df.set_index("Date", inplace=True)
        elif "Datetime" in df.columns:
            df["Datetime"] = pd.to_datetime(df["Datetime"])
            df.set_index("Datetime", inplace=True)
        else:
            # Try to convert current index if possible
            try:
                df.index = pd.to_datetime(df.index)
            except (TypeError, ValueError):
                return df

    # Define aggregation rules
    agg_dict = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }

    # Keep only columns that exist in the aggregation rules
    actual_agg = {
        col: agg_dict[col.lower()] for col in df.columns if col.lower() in agg_dict
    }

    # Perform resampling
    resampled_df = df.resample(freq).agg(actual_agg).dropna()

    return resampled_df


def get_interval_from_timeframe(timeframe: str) -> str:
    """
    Convert timeframe to Yahoo Finance interval.
    """
    mapping = {
        "1mo": "1mo",
        "1wk": "1wk",
        "1d": "1d",
        "60m": "60m",
        "30m": "30m",
        "15m": "15m",
        "5m": "5m",
        "1m": "1m",
    }
    return mapping.get(timeframe, "1d")
