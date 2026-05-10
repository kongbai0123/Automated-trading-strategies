from datetime import datetime

from src.trading.brokers import PaperBrokerAdapter
from src.trading.models import OrderRequest, OrderSide


def _request() -> OrderRequest:
    return OrderRequest(
        order_id="order:1",
        intent_id="intent:1",
        symbol="2330.TW",
        side=OrderSide.BUY,
        order_type="MARKET",
        quantity=100,
        market_time=datetime(2026, 5, 8, 9, 0, 0),
        submitted_at=datetime(2026, 5, 7, 9, 0, 1),
        processed_at=datetime(2026, 5, 7, 9, 0, 2),
    )


def test_paper_broker_can_submit_query_and_cancel_open_orders():
    broker = PaperBrokerAdapter()

    accepted = broker.submit_order(_request())

    assert broker.get_order(accepted.order_id) == accepted
    assert broker.list_open_orders() == [accepted]

    cancelled = broker.cancel_order(accepted.order_id)

    assert cancelled.status.value == "CANCELLED"
    assert broker.list_open_orders() == []


def test_paper_broker_reports_positions_from_filled_orders():
    broker = PaperBrokerAdapter()
    accepted = broker.submit_order(_request())
    filled = broker.apply_fill(accepted, fill_quantity=accepted.quantity)

    positions = broker.get_positions()

    assert filled.status.value == "FILLED"
    assert broker.list_open_orders() == []
    assert len(positions) == 1
    assert positions[0].symbol == "2330.TW"
    assert positions[0].quantity == 100


def test_paper_broker_keeps_partial_fill_open_and_updates_position_incrementally():
    broker = PaperBrokerAdapter()
    accepted = broker.submit_order(_request())

    partial = broker.apply_fill(accepted, fill_quantity=40)
    positions = broker.get_positions()

    assert partial.status.value == "PARTIALLY_FILLED"
    assert partial.remaining_quantity == 60
    assert broker.list_open_orders() == [partial]
    assert positions[0].quantity == 40

    final = broker.apply_fill(partial, fill_quantity=60)

    assert final.status.value == "FILLED"
    assert broker.list_open_orders() == []
    assert broker.get_positions()[0].quantity == 100


def test_paper_broker_rejects_invalid_order_submission():
    broker = PaperBrokerAdapter()
    invalid_request = OrderRequest(
        order_id="order:bad",
        intent_id="intent:bad",
        symbol="2330.TW",
        side=OrderSide.BUY,
        order_type="MARKET",
        quantity=0,
        market_time=datetime(2026, 5, 8, 9, 0, 0),
        submitted_at=datetime(2026, 5, 7, 9, 0, 1),
        processed_at=datetime(2026, 5, 7, 9, 0, 2),
    )

    import pytest

    with pytest.raises(ValueError, match="quantity"):
        broker.submit_order(invalid_request)


def test_paper_broker_rejects_cancelling_non_open_order():
    broker = PaperBrokerAdapter()

    import pytest

    with pytest.raises(ValueError, match="open order"):
        broker.cancel_order("order:missing")
