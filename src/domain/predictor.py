from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import Protocol, runtime_checkable

import numpy as np
import pandas as pd

from src.config.predictor_config import PredictorConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProjectionResult:
    trend_score: float
    trend_reasons: tuple[str, ...]
    risk_score: float
    risk_reason: str
    sentiment: str
    color: str
    scenarios: dict[str, float]
    config_version: str

    def to_dict(self) -> dict:
        return asdict(self)


@runtime_checkable
class IPredictor(Protocol):
    def get_projection(self, dataframe: pd.DataFrame) -> ProjectionResult:
        """Return a deterministic projection for a validated market dataframe."""


class HeuristicPredictor:
    def __init__(self, config: PredictorConfig | None = None) -> None:
        self._config = config or PredictorConfig()

    def get_projection(self, dataframe: pd.DataFrame) -> ProjectionResult:
        self._validate_input(dataframe)
        trend_score, trend_reasons = self._calculate_trend_score(dataframe)
        risk_score, risk_reason = self._calculate_risk_score(dataframe)
        scenarios = self._project_scenarios(dataframe)
        sentiment, color = self._classify_sentiment(trend_score)
        result = ProjectionResult(
            trend_score=trend_score,
            trend_reasons=tuple(trend_reasons),
            risk_score=risk_score,
            risk_reason=risk_reason,
            sentiment=sentiment,
            color=color,
            scenarios=scenarios,
            config_version=self._config.config_version,
        )
        logger.info(
            "prediction_completed config_version=%s data_length=%s trend_score=%.2f risk_score=%.2f sentiment=%s",
            self._config.config_version,
            len(dataframe),
            trend_score,
            risk_score,
            sentiment,
            extra={
                "config_version": self._config.config_version,
                "data_length": len(dataframe),
                "trend_score": trend_score,
                "risk_score": risk_score,
                "sentiment": sentiment,
            },
        )
        return result

    def _validate_input(self, dataframe: pd.DataFrame) -> None:
        if dataframe.empty:
            raise ValueError("Predictor input dataframe is empty.")
        if len(dataframe) < self._config.min_data_length:
            raise ValueError(
                f"Predictor input requires at least {self._config.min_data_length} rows."
            )
        missing = [
            column
            for column in self._config.required_columns
            if column not in dataframe.columns
        ]
        if missing:
            raise ValueError(f"Predictor input missing required columns: {missing}")
        numeric_values = dataframe.loc[:, self._config.required_columns].to_numpy(
            dtype=float
        )
        if not np.isfinite(numeric_values).all():
            raise ValueError("Predictor input values must be finite.")

    def _calculate_trend_score(
        self, dataframe: pd.DataFrame
    ) -> tuple[float, list[str]]:
        latest = dataframe.iloc[-1]
        score = self._config.base_trend_score
        reasons: list[str] = []

        if latest["close"] > latest["sma_20"] > latest["sma_50"]:
            score += self._config.sma_alignment_weight
            reasons.append("price_above_sma_20_and_sma_50")
        elif latest["close"] < latest["sma_20"] < latest["sma_50"]:
            score -= self._config.sma_alignment_weight
            reasons.append("price_below_sma_20_and_sma_50")

        if latest["macd_hist"] > 0:
            score += self._config.macd_weight
            reasons.append("macd_hist_positive")
        else:
            score -= self._config.macd_weight
            reasons.append("macd_hist_non_positive")

        lookback_close = dataframe["close"].iloc[-self._config.momentum_lookback]
        recent_change = (latest["close"] / lookback_close) - 1
        if recent_change > self._config.momentum_threshold:
            score += self._config.momentum_weight
            reasons.append("positive_recent_momentum")
        elif recent_change < -self._config.momentum_threshold:
            score -= self._config.momentum_weight
            reasons.append("negative_recent_momentum")

        return self._clamp_score(score), reasons

    def _calculate_risk_score(self, dataframe: pd.DataFrame) -> tuple[float, str]:
        latest = dataframe.iloc[-1]
        atr_ratio = float(latest["atr_14"] / latest["close"])
        all_atr_ratios = dataframe["atr_14"] / dataframe["close"]
        percentile = float((all_atr_ratios < atr_ratio).mean() * 100)
        if percentile > self._config.high_risk_percentile:
            risk_level = "high"
        elif percentile < self._config.low_risk_percentile:
            risk_level = "low"
        else:
            risk_level = "medium"
        return percentile, f"atr_ratio_percentile={percentile:.1f};risk={risk_level}"

    def _project_scenarios(self, dataframe: pd.DataFrame) -> dict[str, float]:
        latest_close = float(dataframe["close"].iloc[-1])
        atr = float(dataframe["atr_14"].iloc[-1])
        expected_move = atr * self._config.scenario_atr_multiplier
        neutral_move = expected_move * self._config.neutral_move_fraction
        return {
            "bullish": latest_close + expected_move,
            "neutral_upper": latest_close + neutral_move,
            "neutral_lower": latest_close - neutral_move,
            "bearish": latest_close - expected_move,
            "current": latest_close,
        }

    def _classify_sentiment(self, trend_score: float) -> tuple[str, str]:
        if trend_score > self._config.bullish_threshold:
            return "Bullish", "green"
        if trend_score < self._config.bearish_threshold:
            return "Bearish", "red"
        return "Neutral", "gray"

    @staticmethod
    def _clamp_score(score: float) -> float:
        return max(0.0, min(100.0, float(score)))
