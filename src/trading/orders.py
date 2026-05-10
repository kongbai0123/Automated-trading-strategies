from dataclasses import replace

from .models import Order, OrderRequest, OrderStatus


class OrderStateMachine:
    @staticmethod
    def new_order(request: OrderRequest) -> Order:
        if request.quantity <= 0:
            raise ValueError("Order quantity must be positive")
        return Order(
            order_id=request.order_id,
            intent_id=request.intent_id,
            symbol=request.symbol,
            side=request.side,
            order_type=request.order_type,
            quantity=request.quantity,
            filled_quantity=0,
            remaining_quantity=request.quantity,
            status=OrderStatus.NEW,
            submitted_at=request.submitted_at,
            market_time=request.market_time,
            processed_at=request.processed_at,
        )

    @staticmethod
    def accept(order: Order) -> Order:
        if order.status is not OrderStatus.NEW:
            raise ValueError("Order must be NEW before it can transition to ACCEPTED")
        return replace(order, status=OrderStatus.ACCEPTED)

    @staticmethod
    def apply_fill(order: Order, fill_quantity: int) -> Order:
        if order.status not in {OrderStatus.ACCEPTED, OrderStatus.PARTIALLY_FILLED}:
            raise ValueError("Order must be ACCEPTED or PARTIALLY_FILLED before fill application")
        if fill_quantity <= 0:
            raise ValueError("fill_quantity must be positive")
        next_filled = order.filled_quantity + fill_quantity
        if next_filled > order.quantity:
            raise ValueError("Cannot overfill order")
        remaining = order.quantity - next_filled
        status = OrderStatus.FILLED if remaining == 0 else OrderStatus.PARTIALLY_FILLED
        return replace(
            order,
            filled_quantity=next_filled,
            remaining_quantity=remaining,
            status=status,
        )
