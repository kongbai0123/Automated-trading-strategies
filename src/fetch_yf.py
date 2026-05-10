import argparse
import os

import yfinance as yf


def fetch_data(symbol: str, period: str = "5y", interval: str = "1d") -> None:
    print(f"正在抓取 {symbol} 的資料 (期間={period}, 間隔={interval})...")
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval=interval)

    if df.empty:
        print(f"找不到 {symbol} 的相關資料。")
        return

    # Reset index to make Date a column for easier saving
    df.reset_index(inplace=True)

    # Save to data directory
    os.makedirs("data", exist_ok=True)
    filepath = os.path.join("data", f"{symbol}.csv")
    df.to_csv(filepath, index=False)
    print(f"資料已成功儲存至 {filepath} (共 {len(df)} 筆)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch historical data from Yahoo Finance.")
    parser.add_argument(
        "--symbol", type=str, required=True, help="Stock symbol (e.g., 2330.TW or AAPL)"
    )
    parser.add_argument("--period", type=str, default="5y", help="Time period to fetch")
    parser.add_argument("--interval", type=str, default="1d", help="Data interval")

    args = parser.parse_args()
    fetch_data(args.symbol, args.period, args.interval)
