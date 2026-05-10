import os
import glob
import pandas as pd
from data_loader import load_csv
from indicators import add_indicators


def process_file(path: str) -> pd.DataFrame:
    """
    Pipeline to load CSV and calculate all indicators.
    Returns the DataFrame with indicators.
    """
    df = load_csv(path)
    # data_loader's validate_ohlcv already standardizes to lowercase 'open', 'high', 'low', 'close', 'volume'
    df = add_indicators(df)
    return df


if __name__ == "__main__":
    data_dir = "data"
    if not os.path.exists(data_dir):
        print(f"Data directory '{data_dir}' not found.")
        exit(1)

    csv_files = glob.glob(os.path.join(data_dir, "*.csv"))
    # Filter out already processed files if any
    csv_files = [f for f in csv_files if not f.endswith("_with_indicators.csv")]

    if not csv_files:
        print("No CSV files found to process.")

    for file in csv_files:
        print(f"Processing {file}...")
        try:
            df_processed = process_file(file)
            print(f"Success! Generated {len(df_processed.columns)} columns.")
        except Exception as e:
            print(f"Failed to process {file}: {e}")
