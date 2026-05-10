from datetime import datetime

from src.trading.models import FillEvent, OrderSide, PortfolioState
from src.trading.portfolio import PortfolioEngine


def test_portfolio_updates_cash_position_and_average_price():
    portfolio = PortfolioState.initial(cash=1_000_000.0)
    fill = FillEvent(
        fill_id="fill:1",
        order_id="order:1",
        symbol="2330.TW",
        side=OrderSide.BUY,
        fill_quantity=100,
        fill_price=100.0,
        commission=10.0,
        slippage=0.0,
        filled_at=datetime(2026, 5, 7, 9, 1, 0),
        market_time=datetime(2026, 5, 7, 9, 1, 0),
        processed_at=datetime(2026, 5, 7, 9, 1, 1),
    )

    updated = PortfolioEngine().apply_fill(portfolio, fill)

    assert updated.cash == 989990.0
    assert updated.positions["2330.TW"].quantity == 100
    assert updated.positions["2330.TW"].average_price == 100.0
    assert updated.gross_exposure == 10000.0


def test_sell_fill_updates_realized_pnl_and_clears_position():
    portfolio = PortfolioState.initial(cash=1_000_000.0)
    engine = PortfolioEngine()
    bought = engine.apply_fill(
        portfolio,
        FillEvent(
            fill_id="fill:buy",
            order_id="order:buy",
            symbol="2330.TW",
            side=OrderSide.BUY,
            fill_quantity=100,
            fill_price=100.0,
            commission=0.0,
            slippage=0.0,
            filled_at=datetime(2026, 5, 7, 9, 1, 0),
            market_time=datetime(2026, 5, 7, 9, 1, 0),
            processed_at=datetime(2026, 5, 7, 9, 1, 1),
        ),
    )

    sold = engine.apply_fill(
        bought,
        FillEvent(
            fill_id="fill:sell",
            order_id="order:sell",
            symbol="2330.TW",
            side=OrderSide.SELL,
            fill_quantity=100,
            fill_price=110.0,
            commission=0.0,
            slippage=0.0,
            filled_at=datetime(2026, 5, 8, 9, 1, 0),
            market_time=datetime(2026, 5, 8, 9, 1, 0),
            processed_at=datetime(2026, 5, 8, 9, 1, 1),
        ),
    )

    assert sold.cash == 1_001_000.0
    assert sold.realized_pnl == 1_000.0
    assert sold.positions["2330.TW"].quantity == 0
    assert sold.gross_exposure == 0.0


def test_mark_to_market_updates_unrealized_pnl_and_equity():
    portfolio = PortfolioEngine().apply_fill(
        PortfolioState.initial(cash=1_000_000.0),
        FillEvent(
            fill_id="fill:buy",
            order_id="order:buy",
            symbol="2330.TW",
            side=OrderSide.BUY,
            fill_quantity=100,
            fill_price=100.0,
            commission=0.0,
            slippage=0.0,
            filled_at=datetime(2026, 5, 7, 9, 1, 0),
            market_time=datetime(2026, 5, 7, 9, 1, 0),
            processed_at=datetime(2026, 5, 7, 9, 1, 1),
        ),
    )

    marked = PortfolioEngine().mark_to_market(portfolio, {"2330.TW": 110.0})

    assert marked.gross_exposure == 11000.0
    assert marked.unrealized_pnl == 1000.0
    assert marked.equity == 1001000.0
