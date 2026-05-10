from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from src.trading.engine import TradingEngine
from src.trading.models import OrderSide, PortfolioState, SignalEvent, generate_trace_id
from src.ui.components.trade_lifecycle_panel import (
    LifecycleSnapshot,
    build_lifecycle_snapshot,
)


def build_signal_from_analysis(
    result: dict[str, Any],
    *,
    symbol: str,
    strategy_name: str,
    timeframe: str,
    created_at: datetime | None = None,
) -> SignalEvent | None:
    dataframe = result["df"]
    if "signal" not in dataframe.columns:
        return None

    actionable = dataframe[dataframe["signal"].isin([1, -1])]
    if actionable.empty:
        return None

    latest = actionable.iloc[-1]
    market_time = pd.Timestamp(latest.name).to_pydatetime()
    side = OrderSide.BUY if int(latest["signal"]) > 0 else OrderSide.SELL
    reference_price = float(latest.get("close", 0.0))
    created_at = created_at or datetime.now()

    return SignalEvent(
        signal_id=generate_trace_id("signal", strategy_name, symbol, market_time.isoformat()),
        run_id=generate_trace_id("run", symbol, timeframe, created_at.strftime("%Y%m%d")),
        strategy_id=strategy_name,
        symbol=symbol,
        timeframe=timeframe,
        side=side,
        signal_type="ENTRY",
        strength=abs(float(latest["signal"])),
        confidence=0.75,
        market_time=market_time,
        created_at=created_at,
        processed_at=created_at,
        metadata={"reference_price": reference_price},
    )


def build_trade_lifecycle_view_model(
    *,
    journal_events: list,
    portfolio_state: PortfolioState | None,
) -> LifecycleSnapshot:
    return build_lifecycle_snapshot(journal_events, portfolio_state=portfolio_state)


def execute_latest_signal(
    *,
    engine: TradingEngine,
    result: dict[str, Any] | None,
    symbol: str,
    strategy_name: str,
    timeframe: str,
    requested_quantity: int,
) -> tuple[str, str]:
    if not result:
        return "warning", "Run analysis first."

    signal = build_signal_from_analysis(
        result,
        symbol=symbol,
        strategy_name=strategy_name,
        timeframe=timeframe,
    )
    if signal is None:
        return "warning", "No actionable signal found in the current dataset."

    execution_price = float(signal.metadata.get("reference_price", 0.0))
    outcome = engine.process_signal(
        signal,
        requested_quantity=requested_quantity,
        execution_price=execution_price,
    )
    if outcome.order is None:
        return "info", f"Intent stopped at {outcome.intent.status.value}."
    return "success", f"Order {outcome.order.order_id} is {outcome.order.status.value}."
