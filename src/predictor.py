import pandas as pd
import numpy as np


def calculate_trend_score(df: pd.DataFrame) -> tuple:
    """
    計算 AI 趨勢分數 (0-100)。
    基於均線結構、MACD 動能與多週期同步性。
    """
    if df.empty or len(df) < 60:
        return 50, ["資料不足，維持中性評價"]

    latest = df.iloc[-1]
    score = 50
    reasons = []

    # 1. 價格相對於均線位置
    if "sma_20" in df.columns and "sma_50" in df.columns:
        if latest["close"] > latest["sma_20"] > latest["sma_50"]:
            score += 20
            reasons.append("價格與均線呈多頭排列")
        elif latest["close"] < latest["sma_20"] < latest["sma_50"]:
            score -= 20
            reasons.append("價格與均線呈空頭排列")

    # 2. MACD 動能
    if "macd_hist" in df.columns:
        if latest["macd_hist"] > 0:
            score += 10
            reasons.append("MACD 柱狀體維持正向動能")
        else:
            score -= 10
            reasons.append("MACD 動能轉弱或進入負向區")

    # 3. 趨勢延續性 (最近 10 天方向)
    recent_change = (
        (df["close"].iloc[-1] / df["close"].iloc[-10]) - 1 if len(df) >= 10 else 0
    )
    if recent_change > 0.03:
        score += 10
        reasons.append("短期趨勢向上延續中")
    elif recent_change < -0.03:
        score -= 10
        reasons.append("短期趨勢向下修整中")

    return max(0, min(100, score)), reasons


def calculate_risk_score(df: pd.DataFrame) -> tuple:
    """
    計算風險分數 (0-100)。
    基於 ATR 百分位與歷史波動率。
    """
    if df.empty or "atr_14" not in df.columns:
        return 50, ["無法評估風險"]

    latest = df.iloc[-1]
    atr_ratio = latest["atr_14"] / latest["close"]

    # 計算 ATR 比例的歷史百分位
    all_atr_ratios = df["atr_14"] / df["close"]
    percentile = (all_atr_ratios < atr_ratio).mean() * 100

    score = percentile
    level = "中"
    if score > 70:
        level = "高"
    elif score < 30:
        level = "低"

    reason = f"波動率處於歷史 {percentile:.1f}% 分位 ({level}風險)"
    return score, reason


def project_scenarios(df: pd.DataFrame, days: int = 10) -> dict:
    """
    基於 ATR 與波動率推演未來情境。
    """
    if df.empty or "atr_14" not in df.columns:
        return {}

    latest_close = df["close"].iloc[-1]
    atr = df["atr_14"].iloc[-1]

    # 預期波動區間 (±2.0 * ATR 為大概率邊界)
    expected_move = atr * 1.5

    return {
        "bullish": latest_close + expected_move,
        "neutral_upper": latest_close + (expected_move * 0.3),
        "neutral_lower": latest_close - (expected_move * 0.3),
        "bearish": latest_close - expected_move,
        "current": latest_close,
    }


def get_ai_projection(df: pd.DataFrame) -> dict:
    """
    整合 AI 趨勢推演結果。
    """
    trend_score, trend_reasons = calculate_trend_score(df)
    risk_score, risk_reason = calculate_risk_score(df)
    scenarios = project_scenarios(df)

    # 判定綜合情境
    if trend_score > 65:
        sentiment = "樂觀 (Bullish)"
        color = "green"
    elif trend_score < 35:
        sentiment = "保守 (Bearish)"
        color = "red"
    else:
        sentiment = "中性 (Neutral)"
        color = "gray"

    return {
        "trend_score": trend_score,
        "trend_reasons": trend_reasons,
        "risk_score": risk_score,
        "risk_reason": risk_reason,
        "sentiment": sentiment,
        "color": color,
        "scenarios": scenarios,
    }


# Keep the old functions for backward compatibility if needed, but update their logic
def get_investment_advice(df: pd.DataFrame) -> dict:
    projection = get_ai_projection(df)

    # Map projection to the old advice format
    return {
        "score": projection["trend_score"],
        "advice": projection["sentiment"],
        "color": projection["color"],
        "reasons": projection["trend_reasons"] + [projection["risk_reason"]],
    }


def predict_future_prices(df: pd.DataFrame, days_to_predict: int = 10) -> pd.DataFrame:
    """
    Modified to provide scenario-based bounds instead of linear regression.
    """
    if df.empty or "atr_14" not in df.columns:
        return pd.DataFrame()

    latest_close = df["close"].iloc[-1]
    atr = df["atr_14"].iloc[-1]

    last_date = df.index[-1]
    future_dates = pd.date_range(
        start=last_date + pd.Timedelta(days=1), periods=days_to_predict, freq="B"
    )

    # 隨著時間增加，不確定性擴大 (sqrt of time)
    time_steps = np.sqrt(np.arange(1, days_to_predict + 1))
    upper_bounds = latest_close + (atr * 1.5 * time_steps)
    lower_bounds = latest_close - (atr * 1.5 * time_steps)

    # 預測價格維持在中軸 (中性假設)
    predictions = np.full(days_to_predict, latest_close)

    return pd.DataFrame(
        {
            "date": future_dates,
            "predicted_price": predictions,
            "upper_bound": upper_bounds,
            "lower_bound": lower_bounds,
        }
    )
