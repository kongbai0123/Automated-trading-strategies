from dataclasses import replace

from .events import EventType, JournalEvent
from .models import FillEvent, OrderSide, PortfolioState, PositionState


class PortfolioEngine:
    def apply_fill(self, portfolio: PortfolioState, fill: FillEvent) -> PortfolioState:
        positions = dict(portfolio.positions)
        current = positions.get(
            fill.symbol,
            PositionState(symbol=fill.symbol, quantity=0, average_price=0.0),
        )

        realized_pnl = portfolio.realized_pnl
        cash = portfolio.cash

        if fill.side is OrderSide.BUY:
            total_cost = (
                (fill.fill_quantity * fill.fill_price) + fill.commission + fill.slippage
            )
            next_quantity = current.quantity + fill.fill_quantity
            next_average = (
                (
                    (current.quantity * current.average_price)
                    + (fill.fill_quantity * fill.fill_price)
                )
                / next_quantity
                if next_quantity
                else 0.0
            )
            positions[fill.symbol] = replace(
                current, quantity=next_quantity, average_price=next_average
            )
            cash -= total_cost
        else:
            if fill.fill_quantity > current.quantity:
                raise ValueError("Sell fill exceeds current position quantity")
            proceeds = (
                (fill.fill_quantity * fill.fill_price) - fill.commission - fill.slippage
            )
            cash += proceeds
            realized_pnl += (
                fill.fill_price - current.average_price
            ) * fill.fill_quantity
            next_quantity = current.quantity - fill.fill_quantity
            next_average = current.average_price if next_quantity else 0.0
            positions[fill.symbol] = replace(
                current, quantity=next_quantity, average_price=next_average
            )

        if cash < 0:
            raise ValueError("Cash cannot become negative after fill application")

        gross_exposure = sum(
            position.quantity * position.average_price
            for position in positions.values()
        )
        equity = cash + gross_exposure
        return PortfolioState(
            cash=cash,
            positions=positions,
            realized_pnl=realized_pnl,
            unrealized_pnl=0.0,
            equity=equity,
            gross_exposure=gross_exposure,
        )

    def mark_to_market(
        self, portfolio: PortfolioState, market_prices: dict[str, float]
    ) -> PortfolioState:
        gross_exposure = 0.0
        unrealized_pnl = 0.0
        for symbol, position in portfolio.positions.items():
            mark_price = market_prices.get(symbol, position.average_price)
            gross_exposure += position.quantity * mark_price
            unrealized_pnl += (mark_price - position.average_price) * position.quantity

        return PortfolioState(
            cash=portfolio.cash,
            positions=dict(portfolio.positions),
            realized_pnl=portfolio.realized_pnl,
            unrealized_pnl=unrealized_pnl,
            equity=portfolio.cash + gross_exposure,
            gross_exposure=gross_exposure,
        )

    def replay(self, events: list[JournalEvent]) -> PortfolioState:
        init_event = next(
            (
                event
                for event in events
                if event.event_type is EventType.PORTFOLIO_INITIALIZED
            ),
            None,
        )
        if init_event is None:
            raise ValueError("Replay requires PORTFOLIO_INITIALIZED event")

        portfolio = PortfolioState.initial(cash=init_event.payload["starting_cash"])
        for event in events:
            if event.event_type is not EventType.FILL_RECORDED:
                continue

            payload = event.payload
            fill = FillEvent(
                fill_id=payload["fill_id"],
                order_id=payload["order_id"],
                symbol=payload["symbol"],
                side=OrderSide(payload["side"]),
                fill_quantity=payload["fill_quantity"],
                fill_price=payload["fill_price"],
                commission=payload["commission"],
                slippage=payload["slippage"],
                filled_at=payload["filled_at"],
                market_time=payload["market_time"],
                processed_at=payload["processed_at"],
            )
            portfolio = self.apply_fill(portfolio, fill)
        return portfolio
