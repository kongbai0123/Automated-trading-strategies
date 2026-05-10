import pandas as pd
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))
from indicators import calculate_sma, calculate_rsi


def test_calculate_sma():
    series = pd.Series([1, 2, 3, 4, 5])
    sma = calculate_sma(series, 3)

    assert pd.isna(sma[0])
    assert pd.isna(sma[1])
    assert sma[2] == 2.0
    assert sma[3] == 3.0
    assert sma[4] == 4.0


def test_calculate_rsi():
    # A simple upward trend should have RSI near 100
    series = pd.Series(range(1, 20))
    rsi = calculate_rsi(series, 14)

    assert pd.isna(rsi[0])  # delta is NaN for the first element
    assert rsi.iloc[-1] > 99.0  # Pure upward trend

    # A pure downward trend should have RSI near 0
    series_down = pd.Series(range(20, 1, -1))
    rsi_down = calculate_rsi(series_down, 14)
    assert rsi_down.iloc[-1] < 1.0


def test_pure_function_no_side_effects():
    original_series = pd.Series([1, 2, 3, 4, 5])
    copy_series = original_series.copy()

    calculate_sma(original_series, 3)

    # Assert original series is unchanged
    pd.testing.assert_series_equal(original_series, copy_series)
