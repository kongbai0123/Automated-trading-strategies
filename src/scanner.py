import pandas as pd
from .chips_provider import get_latest_chips, get_chip_score

def analyze_symbol_detailed(df: pd.DataFrame, symbol: str = "") -> dict:
    """
    Perform multi-dimensional analysis on a single symbol's DataFrame.
    Returns a dictionary of metrics and scores.
    """
    if df.empty:
        return {"score": 0, "reason": "無資料", "trend": "未知", "risk": "未知"}

    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest
    
    score = 0
    reasons = []
    
    # 1. 價格結構檢測 (Price Structure)
    trend = "橫盤"
    if 'sma_20' in df.columns and 'sma_60' in df.columns:
        if latest['close'] > latest['sma_20'] > latest['sma_60']:
            score += 25
            trend = "多頭排列"
            reasons.append("價格 20/60MA 多頭排列")
        elif latest['close'] < latest['sma_20'] < latest['sma_60']:
            score -= 20
            trend = "空頭排列"
            reasons.append("價格 20/60MA 空頭排列")

    # 2. 動能檢測 (Momentum)
    if 'rsi_14' in df.columns:
        rsi = latest['rsi_14']
        if rsi < 30:
            score += 15
            reasons.append(f"RSI({rsi:.1f}) 超賣")
        elif rsi > 70:
            score -= 10
            reasons.append(f"RSI({rsi:.1f}) 超買")
            
    # 3. 成交量檢測 (Volume)
    if 'volume' in df.columns:
        avg_vol = df['volume'].tail(20).mean()
        vol_ratio = latest['volume'] / avg_vol if avg_vol > 0 else 1
        if vol_ratio > 2.0:
            score += 15
            reasons.append(f"量能爆發 ({vol_ratio:.1f}x)")
        elif vol_ratio > 1.5:
            score += 8
            reasons.append(f"量能增溫 ({vol_ratio:.1f}x)")

    # 4. 籌碼檢測 (Chip Data - TW only)
    if symbol and (".TW" in symbol or ".TWO" in symbol):
        chips = get_latest_chips(symbol)
        chip_score, chip_reason = get_chip_score(chips)
        score += chip_score
        if chip_reason != "無明顯變動":
            reasons.append(f"籌碼: {chip_reason}")

    # 5. 波動檢測 (Volatility / Risk)
    risk = "中"
    if 'close' in df.columns:
        pct_change = abs(latest['close'] - prev['close']) / prev['close'] if prev['close'] > 0 else 0
        if pct_change > 0.04:
            risk = "高"
            score -= 5
        elif pct_change < 0.01:
            risk = "低"
            score += 5

    # Final Adjustment
    score = max(0, min(100, score))
    
    return {
        "score": score,
        "trend": trend,
        "volume_ratio": vol_ratio if 'volume' in df.columns else 1.0,
        "risk": risk,
        "reason": " | ".join(reasons) if reasons else "盤整中"
    }
