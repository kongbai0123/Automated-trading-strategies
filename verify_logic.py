import pandas as pd
import numpy as np
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from scanner import analyze_symbol_detailed
from predictor import get_ai_projection

def test_pipeline():
    print("--- 正在驗證交易系統核心邏輯 ---")
    
    # Create dummy OHLCV data
    dates = pd.date_range(start='2026-01-01', periods=100)
    data = {
        'open': np.random.uniform(500, 600, 100),
        'high': np.random.uniform(600, 650, 100),
        'low': np.random.uniform(450, 500, 100),
        'close': np.linspace(500, 600, 100) + np.random.normal(0, 5, 100),
        'volume': np.random.uniform(10000, 50000, 100)
    }
    df = pd.DataFrame(data, index=dates)
    
    # Add indicators (mocking indicators.py logic)
    df['sma_20'] = df['close'].rolling(20).mean()
    df['sma_60'] = df['close'].rolling(60).mean()
    df['rsi_14'] = np.random.uniform(30, 70, 100)
    df['macd_hist'] = np.random.uniform(-1, 1, 100)
    df['atr_14'] = df['close'].rolling(14).std()
    
    print("1. 驗證多維度掃描引擎...")
    analysis = analyze_symbol_detailed(df, symbol="2330.TW")
    print(f"   [OK] 分數: {analysis['score']}, 趨勢: {analysis['trend']}, 風險: {analysis['risk']}")
    print(f"   [OK] 分析依據: {analysis['reason']}")
    
    print("\n2. 驗證 AI 情境推演模型...")
    projection = get_ai_projection(df)
    print(f"   [OK] AI 情緒: {projection['sentiment']}, 趨勢分數: {projection['trend_score']}")
    print(f"   [OK] 預期情境: {projection['scenarios']}")
    
    print("\n--- 核心程序驗證成功 ---")

if __name__ == "__main__":
    test_pipeline()
