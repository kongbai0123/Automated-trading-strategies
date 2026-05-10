from __future__ import annotations

import logging

import numpy as np
import pandas as pd
import pytest

from src.config.predictor_config import PredictorConfig
from src.domain.predictor import HeuristicPredictor, IPredictor, ProjectionResult


def _market_frame(rows: int = 80) -> pd.DataFrame:
    close = np.linspace(100.0, 120.0, rows)
    return pd.DataFrame(
        {
            "open": close - 0.5,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": np.full(rows, 1000),
            "sma_20": close - 2.0,
            "sma_50": close - 5.0,
            "macd_hist": np.full(rows, 0.2),
            "atr_14": np.full(rows, 2.0),
        },
        index=pd.date_range("2026-01-01", periods=rows, freq="D"),
    )


def test_heuristic_predictor_implements_protocol_and_returns_projection() -> None:
    predictor: IPredictor = HeuristicPredictor()

    result = predictor.get_projection(_market_frame())

    assert isinstance(result, ProjectionResult)
    assert result.trend_score > 65
    assert result.sentiment == "Bullish"
    assert result.color == "green"
    assert result.scenarios["bullish"] > result.scenarios["current"]


def test_predictor_rejects_short_dataset_fail_fast() -> None:
    predictor = HeuristicPredictor()

    with pytest.raises(ValueError, match="at least 60 rows"):
        predictor.get_projection(_market_frame(rows=20))


def test_predictor_rejects_nan_and_infinite_values() -> None:
    dataframe = _market_frame()
    dataframe.loc[dataframe.index[-1], "atr_14"] = np.inf

    with pytest.raises(ValueError, match="finite"):
        HeuristicPredictor().get_projection(dataframe)


def test_predictor_rejects_missing_required_columns() -> None:
    dataframe = _market_frame().drop(columns=["macd_hist"])

    with pytest.raises(ValueError, match="missing required columns"):
        HeuristicPredictor().get_projection(dataframe)


def test_predictor_is_deterministic_for_same_input() -> None:
    predictor = HeuristicPredictor()
    dataframe = _market_frame()

    first = predictor.get_projection(dataframe)
    second = predictor.get_projection(dataframe)

    assert first == second


def test_predictor_config_drives_thresholds_and_weights() -> None:
    config = PredictorConfig(
        bullish_threshold=90,
        bearish_threshold=10,
        sma_alignment_weight=5,
        macd_weight=0,
        momentum_weight=0,
    )

    result = HeuristicPredictor(config=config).get_projection(_market_frame())

    assert result.trend_score == 55
    assert result.sentiment == "Neutral"
    assert result.config_version == config.config_version


def test_predictor_emits_structured_log(caplog: pytest.LogCaptureFixture) -> None:
    predictor = HeuristicPredictor()

    with caplog.at_level(logging.INFO, logger="src.domain.predictor"):
        predictor.get_projection(_market_frame())

    assert "prediction_completed" in caplog.text
    assert "config_version" in caplog.text
