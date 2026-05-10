import subprocess
import time

# 定義要導入的全球市場標的清單
MARKET_UNIVERSE = {
    "台股精選": ["2317.TW", "2454.TW", "0050.TW"],
    "美股巨頭": ["AAPL", "MSFT", "TSLA", "NVDA"],
    "加密貨幣": ["BTC-USD", "ETH-USD"],
    "外匯匯率": ["TWD=X"],
}


def run_batch_fetch():
    print("==========================================")
    print("       全球市場資料自動導入工具")
    print("==========================================")

    total_count = sum(len(symbols) for symbols in MARKET_UNIVERSE.values())
    current = 0

    for category, symbols in MARKET_UNIVERSE.items():
        print(f"\n--- 正在處理：{category} ---")
        for symbol in symbols:
            current += 1
            print(f"[{current}/{total_count}] 正在抓取 {symbol}...")

            # 呼叫現有的 fetch_yf.py 腳本
            try:
                subprocess.run(
                    ["py", "src/fetch_yf.py", "--symbol", symbol, "--period", "5y"],
                    check=True,
                )
                # 稍微停頓避免過快請求被阻擋
                time.sleep(1)
            except Exception as e:
                print(f"抓取 {symbol} 時發生錯誤: {e}")

    print("\n==========================================")
    print("       所有市場資料已導入完成！")
    print("==========================================")


if __name__ == "__main__":
    run_batch_fetch()
