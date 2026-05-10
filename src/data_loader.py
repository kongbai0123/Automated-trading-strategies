import os

import pandas as pd


def validate_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validate the DataFrame to ensure it has the correct OHLCV format.
    Ensures 'Date' is index or column, and contains required columns.
    """
    required_cols = {"Open", "High", "Low", "Close", "Volume"}

    if not required_cols.issubset(set(df.columns)):
        # Try checking lowercase version just in case
        lower_required = {c.lower() for c in required_cols}
        if not lower_required.issubset({c.lower() for c in df.columns}):
            raise ValueError(f"DataFrame must contain columns: {required_cols}")

    # Convert all columns to lowercase
    df.columns = df.columns.str.lower()

    if df.isnull().values.any():
        df = df.dropna()

    if not isinstance(df.index, pd.DatetimeIndex):
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df.set_index("date", inplace=True)
        else:
            raise ValueError("DataFrame must have a DatetimeIndex or a 'date' column.")

    # Sort by date just in case
    df = df.sort_index()
    return df


def load_csv(filepath: str) -> pd.DataFrame:
    """
    Load OHLCV data from a CSV file.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    df = pd.read_csv(filepath)
    return validate_ohlcv(df)
