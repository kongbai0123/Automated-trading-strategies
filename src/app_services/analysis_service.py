from __future__ import annotations

from typing import Any

from src.scanner import analyze_symbol_detailed
from src.ui_pipeline import run_backtest_pipeline


def load_analysis(
    *,
    symbol: str,
    strategy_name: str,
    period: str,
    interval: str,
    transaction_cost: float,
) -> dict[str, Any]:
    return run_backtest_pipeline(
        symbol=symbol,
        strategy_name=strategy_name,
        strategy_params={},
        transaction_cost=transaction_cost,
        period=period,
        interval=interval,
    )


def build_kpis(result: dict[str, Any]) -> dict[str, str]:
    kpi = result["kpi"]
    return {
        "Return": f"{float(kpi.get('return', 0.0)):.2%}",
        "Win Rate": f"{float(kpi.get('win_rate', 0.0)):.2%}",
        "Max Drawdown": f"{float(kpi.get('max_drawdown', 0.0)):.2%}",
        "Signal": (
            str(int(result["df"]["signal"].iloc[-1]))
            if "signal" in result["df"].columns
            else "0"
        ),
    }


def build_scanner_rows(
    result: dict[str, Any], *, symbol: str, strategy_name: str
) -> list[dict[str, object]]:
    analysis = analyze_symbol_detailed(result["df"], symbol=symbol)
    latest_close = float(result["df"]["close"].iloc[-1])
    return [
        {
            "symbol": symbol,
            "strategy": strategy_name,
            "score": analysis.get("score", 0),
            "trend": analysis.get("trend", "Unknown"),
            "risk": analysis.get("risk", "Unknown"),
            "last_price": latest_close,
            "reason": analysis.get("reason", ""),
        }
    ]
