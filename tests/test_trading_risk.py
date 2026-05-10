from datetime import datetime, timedelta

from src.trading.models import (
    DecisionStatus,
    OrderIntent,
    OrderRequest,
    OrderSide,
    PortfolioState,
    PositionState,
    SignalEvent,
    generate_trace_id,
)
from src.trading.risk import RiskConfig, RiskEngine


def _signal() -> SignalEvent:
    return SignalEvent(
        signal_id="signal:1",
        run_id="run-1",
        strategy_id="ma-cross",
        symbol="2330.TW",
        timeframe="1d",
        side=OrderSide.BUY,
        signal_type="ENTRY",
        strength=1.0,
        confidence=0.9,
        market_time=datetime(2026, 5, 7, 9, 0, 0),
        created_at=datetime(2026, 5, 7, 9, 0, 1),
        processed_at=datetime(2026, 5, 7, 9, 0, 2),
        metadata={},
    )


def _intent(
    requested_quantity: int,
    *,
    market_time: datetime | None = None,
    expires_at: datetime | None = None,
) -> OrderIntent:
    signal = _signal()
    if market_time is not None:
        signal = SignalEvent(
            signal_id=signal.signal_id,
            run_id=signal.run_id,
            strategy_id=signal.strategy_id,
            symbol=signal.symbol,
            timeframe=signal.timeframe,
            side=signal.side,
            signal_type=signal.signal_type,
            strength=signal.strength,
            confidence=signal.confidence,
            market_time=market_time,
            created_at=signal.created_at,
            processed_at=signal.processed_at,
            metadata=signal.metadata,
        )

    return OrderIntent.from_signal(
        signal=signal,
        intent_id=generate_trace_id("intent", signal.signal_id, "market"),
        quantity_policy="fixed_units",
        requested_quantity=requested_quantity,
        order_type="MARKET",
        reason="entry signal",
        expires_at=expires_at or datetime(2026, 5, 8, 9, 0, 0),
    )


def _risk_engine() -> RiskEngine:
    return RiskEngine(
        RiskConfig(
            max_position_size=100,
            max_symbol_exposure=50_000.0,
            max_total_exposure=50_000.0,
            max_daily_loss=50_000.0,
            semi_auto=True,
        )
    )


def test_risk_rejects_excess_position_size():
    decision = _risk_engine().evaluate(
        intent=_intent(1000),
        portfolio=PortfolioState.initial(cash=1_000_000.0),
        open_orders=[],
    )

    assert decision.approved is False
    assert decision.decision_status is DecisionStatus.REJECTED
    assert "max_position_size" in decision.constraints_checked
    assert "max_position_size" in decision.reject_reasons


def test_risk_rejects_gross_exposure_breach():
    decision = _risk_engine().evaluate(
        intent=_intent(10),
        portfolio=PortfolioState(
            cash=1_000_000.0,
            positions={
                "2330.TW": PositionState(symbol="2330.TW", quantity=490, average_price=100.0),
            },
            realized_pnl=0.0,
            unrealized_pnl=0.0,
            equity=1_000_000.0,
            gross_exposure=49_000.0,
        ),
        open_orders=[],
        reference_price=200.0,
    )

    assert decision.approved is False
    assert "max_total_exposure" in decision.reject_reasons


def test_risk_rejects_when_cash_is_insufficient():
    decision = _risk_engine().evaluate(
        intent=_intent(10),
        portfolio=PortfolioState.initial(cash=500.0),
        open_orders=[],
        reference_price=100.0,
    )

    assert decision.approved is False
    assert "cash_constraint" in decision.reject_reasons


def test_risk_rejects_duplicate_open_order():
    open_order = OrderRequest(
        order_id="order:1",
        intent_id="intent:1",
        symbol="2330.TW",
        side=OrderSide.BUY,
        order_type="MARKET",
        quantity=5,
        market_time=datetime(2026, 5, 8, 9, 0, 0),
        submitted_at=datetime(2026, 5, 7, 9, 0, 1),
        processed_at=datetime(2026, 5, 7, 9, 0, 2),
    )
    decision = _risk_engine().evaluate(
        intent=_intent(10),
        portfolio=PortfolioState.initial(cash=1_000_000.0),
        open_orders=[open_order],
        reference_price=100.0,
    )

    assert decision.approved is False
    assert "duplicate_open_order" in decision.reject_reasons


def test_risk_rejects_expired_intent():
    market_time = datetime(2026, 5, 9, 9, 0, 0)
    decision = _risk_engine().evaluate(
        intent=_intent(
            10,
            market_time=market_time,
            expires_at=market_time - timedelta(minutes=1),
        ),
        portfolio=PortfolioState.initial(cash=1_000_000.0),
        open_orders=[],
        reference_price=100.0,
    )

    assert decision.approved is False
    assert "intent_expired" in decision.reject_reasons


def test_risk_rejects_daily_loss_limit_breach():
    decision = _risk_engine().evaluate(
        intent=_intent(10),
        portfolio=PortfolioState(
            cash=1_000_000.0,
            positions={},
            realized_pnl=-60_000.0,
            unrealized_pnl=0.0,
            equity=940_000.0,
            gross_exposure=0.0,
        ),
        open_orders=[],
        reference_price=100.0,
    )

    assert decision.approved is False
    assert "max_daily_loss" in decision.reject_reasons
