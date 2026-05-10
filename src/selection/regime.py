from enum import Enum


class MarketRegime(str, Enum):
    TRENDING = "TRENDING"
    BALANCED = "BALANCED"
    RISK_OFF = "RISK_OFF"


class RegimeFilter:
    def classify(self, *, trend_score: float, volatility_score: float) -> MarketRegime:
        if volatility_score >= 0.85:
            return MarketRegime.RISK_OFF
        if trend_score >= 0.65:
            return MarketRegime.TRENDING
        return MarketRegime.BALANCED
