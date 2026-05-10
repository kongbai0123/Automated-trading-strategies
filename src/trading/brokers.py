from dataclasses import replace

from .models import BrokerPosition, Order, OrderStatus
from .orders import OrderStateMachine


class PaperBrokerAdapter:
    def __init__(self) -> None:
        self._open_orders: dict[str, Order] = {}
        self._all_orders: dict[str, Order] = {}
        self._positions: dict[str, int] = {}

    def submit_order(self, order_request) -> Order:
        order = OrderStateMachine.accept(OrderStateMachine.new_order(order_request))
        self._open_orders[order.order_id] = order
        self._all_orders[order.order_id] = order
        return order

    def cancel_order(self, order_id: str) -> Order:
        if order_id not in self._open_orders:
            raise ValueError(f"Cannot cancel non-open order: {order_id}")
        order = self._open_orders.pop(order_id)
        cancelled = replace(order, status=OrderStatus.CANCELLED)
        self._all_orders[order_id] = cancelled
        return cancelled

    def get_order(self, order_id: str) -> Order:
        return self._all_orders[order_id]

    def list_open_orders(self) -> list[Order]:
        return list(self._open_orders.values())

    def apply_fill(self, order: Order, *, fill_quantity: int) -> Order:
        filled_order = OrderStateMachine.apply_fill(order, fill_quantity=fill_quantity)
        self._all_orders[order.order_id] = filled_order
        if filled_order.status is OrderStatus.FILLED:
            self._open_orders.pop(order.order_id, None)
        else:
            self._open_orders[order.order_id] = filled_order

        signed_quantity = fill_quantity if filled_order.side.value == "BUY" else -fill_quantity
        self._positions[filled_order.symbol] = (
            self._positions.get(filled_order.symbol, 0) + signed_quantity
        )
        return filled_order

    def get_positions(self) -> list[BrokerPosition]:
        return [
            BrokerPosition(symbol=symbol, quantity=quantity)
            for symbol, quantity in self._positions.items()
            if quantity != 0
        ]
