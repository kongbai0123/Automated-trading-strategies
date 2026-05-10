from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PredictorConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    config_version: str = "heuristic-v1"
    required_columns: tuple[str, ...] = (
        "open",
        "high",
        "low",
        "close",
        "volume",
        "sma_20",
        "sma_50",
        "macd_hist",
        "atr_14",
    )
    min_data_length: int = Field(default=60, ge=2)
    base_trend_score: float = Field(default=50.0, ge=0.0, le=100.0)
    bullish_threshold: float = Field(default=65.0, ge=0.0, le=100.0)
    bearish_threshold: float = Field(default=35.0, ge=0.0, le=100.0)
    sma_alignment_weight: float = Field(default=20.0, ge=0.0)
    macd_weight: float = Field(default=10.0, ge=0.0)
    momentum_weight: float = Field(default=10.0, ge=0.0)
    momentum_lookback: int = Field(default=10, ge=1)
    momentum_threshold: float = Field(default=0.03, ge=0.0)
    scenario_atr_multiplier: float = Field(default=1.5, gt=0.0)
    neutral_move_fraction: float = Field(default=0.3, ge=0.0, le=1.0)
    high_risk_percentile: float = Field(default=70.0, ge=0.0, le=100.0)
    low_risk_percentile: float = Field(default=30.0, ge=0.0, le=100.0)

    @model_validator(mode="after")
    def validate_threshold_order(self) -> "PredictorConfig":
        if self.bearish_threshold >= self.bullish_threshold:
            raise ValueError("bearish_threshold must be lower than bullish_threshold")
        if self.low_risk_percentile >= self.high_risk_percentile:
            raise ValueError(
                "low_risk_percentile must be lower than high_risk_percentile"
            )
        if self.momentum_lookback >= self.min_data_length:
            raise ValueError("momentum_lookback must be lower than min_data_length")
        return self
