from datetime import datetime

import pytest

from src.trading.execution import NextBarExecutionPolicy
from src.trading.models import OrderRequest, OrderSide
from src.trading.orders import OrderStateMachine


def _request() -> OrderRequest:
    return OrderRequest(
        order_id="order:1",
        intent_id="intent:1",
        symbol="2330.TW",
        side=OrderSide.BUY,
        order_type="MARKET",
        quantity=100,
        market_time=datetime(2026, 5, 7, 9, 1, 0),
        submitted_at=datetime(2026, 5, 7, 9, 1, 1),
        processed_at=datetime(2026, 5, 7, 9, 1, 2),
    )


def test_order_lifecycle_market_fill():
    order = OrderStateMachine.new_order(_request())

    accepted = OrderStateMachine.accept(order)
    filled = OrderStateMachine.apply_fill(accepted, fill_quantity=100)

    assert accepted.status.value == "ACCEPTED"
    assert filled.status.value == "FILLED"
    assert filled.remaining_quantity == 0


def test_order_rejects_fill_before_accept():
    order = OrderStateMachine.new_order(_request())

    with pytest.raises(ValueError, match="ACCEPTED"):
        OrderStateMachine.apply_fill(order, fill_quantity=10)


def test_order_rejects_overfill():
    order = OrderStateMachine.accept(OrderStateMachine.new_order(_request()))

    with pytest.raises(ValueError, match="overfill"):
        OrderStateMachine.apply_fill(order, fill_quantity=101)


def test_next_bar_execution_policy():
    policy = NextBarExecutionPolicy()

    executable_at = policy.next_market_time(datetime(2026, 5, 7, 9, 0, 0), timeframe="1d")

    assert executable_at == datetime(2026, 5, 8, 9, 0, 0)
