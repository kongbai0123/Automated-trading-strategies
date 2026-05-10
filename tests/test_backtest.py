import pytest
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))
from backtest import BacktestEngine
from analytics import calculate_kpi


def test_backtest_engine_t_plus_1():
    # Mock data where price goes up by 10 each day
    df = pd.DataFrame(
        {
            "close": [100, 110, 120, 130, 140],
            "signal": [
                0,
                1,
                0,
                -1,
                0,
            ],  # Buy on day 1 (exec day 2), Sell on day 3 (exec day 4)
        }
    )

    engine = BacktestEngine(transaction_cost=0.0)  # no cost for simpler calculation
    out = engine.run(df)

    # Position should carry forward
    assert out["position"].tolist() == [0.0, 1.0, 1.0, -1.0, -1.0]

    # Strategy returns should execute at T+1
    # Day 0: NaN
    # Day 1: ret=0.1, pos(T-1)=0 -> strat_ret=0
    # Day 2: ret=0.0909, pos(T-1)=1 -> strat_ret=0.0909
    assert out["strategy_returns"].iloc[1] == 0.0
    assert out["strategy_returns"].iloc[2] > 0.0


def test_calculate_kpi():
    df = pd.DataFrame(
        {"equity": [1.0, 1.1, 0.9, 1.5], "strategy_returns": [0.0, 0.1, -0.18, 0.66]}
    )

    kpi = calculate_kpi(df)
    assert kpi["total_return"] == 0.5
    assert kpi["max_drawdown"] < 0.0
    assert kpi["sharpe"] != 0.0


def test_calculate_kpi_trade_metrics_exclude_flat_periods():
    df = pd.DataFrame(
        {
            "equity": [1.0, 1.0, 1.1, 1.1, 1.0, 1.0],
            "strategy_returns": [0.0, 0.0, 0.1, 0.0, -0.1, 0.0],
            "position": [0, 1, 1, 0, -1, 0],
        }
    )

    kpi = calculate_kpi(df)

    assert kpi["total_trades"] == 4
    assert kpi["exposure"] == pytest.approx(0.5)
    assert kpi["win_rate"] == pytest.approx(0.5)
    assert kpi["profit_factor"] == pytest.approx(1.0)
