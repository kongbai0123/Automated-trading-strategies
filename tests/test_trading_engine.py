from datetime import datetime

import pytest

from src.trading.events import EventType
from src.trading.engine import TradingEngine
from src.trading.journal import InMemoryJournal
from src.trading.models import OrderSide, SignalEvent
from src.trading.risk import RiskConfig


def _build_signal(signal_id: str) -> SignalEvent:
    return SignalEvent(
        signal_id=signal_id,
        run_id="run-1",
        strategy_id="ma-cross",
        symbol="2330.TW",
        timeframe="1d",
        side=OrderSide.BUY,
        signal_type="ENTRY",
        strength=0.8,
        confidence=0.8,
        market_time=datetime(2026, 5, 7, 9, 0, 0),
        created_at=datetime(2026, 5, 7, 9, 0, 1),
        processed_at=datetime(2026, 5, 7, 9, 0, 2),
        metadata={},
    )


def _risk_config(semi_auto: bool) -> RiskConfig:
    return RiskConfig(
        max_position_size=100,
        max_symbol_exposure=50_000.0,
        max_total_exposure=50_000.0,
        max_daily_loss=50_000.0,
        semi_auto=semi_auto,
    )


def test_semi_auto_stops_at_pending_approval_and_rejects_duplicate_signal():
    journal = InMemoryJournal()
    engine = TradingEngine.for_semi_auto(
        risk_config=_risk_config(semi_auto=True),
        journal=journal,
        starting_cash=1_000_000.0,
    )
    signal = _build_signal("signal:pending")

    first = engine.process_signal(signal, requested_quantity=10)
    second = engine.process_signal(signal, requested_quantity=10)

    assert first.intent.status.value == "PENDING_APPROVAL"
    assert first.order is None
    assert second.intent.status.value == "RISK_REJECTED"
    assert second.risk_decision.approved is False
    assert "duplicate_signal" in second.risk_decision.reject_reasons


def test_paper_flow_emits_full_audit_chain_and_replays_portfolio():
    journal = InMemoryJournal()
    engine = TradingEngine.for_paper_trading(
        risk_config=_risk_config(semi_auto=False),
        journal=journal,
        starting_cash=1_000_000.0,
    )
    signal = _build_signal("signal:audit")

    result = engine.process_signal(signal, requested_quantity=10, execution_price=100.0)
    replayed = engine.replay_portfolio(journal.read_all())
    event_types = [event.event_type.value for event in journal.read_all()]

    assert result.order is not None
    assert event_types == [
        "PORTFOLIO_INITIALIZED",
        "SIGNAL_EMITTED",
        "INTENT_CREATED",
        "RISK_APPROVED",
        "INTENT_APPROVED_FOR_EXECUTION",
        "ORDER_SUBMITTED",
        "ORDER_ACCEPTED",
        "ORDER_FILLED",
        "FILL_RECORDED",
        "PORTFOLIO_UPDATED",
        "PORTFOLIO_SNAPSHOT",
    ]
    assert replayed.positions["2330.TW"].quantity == 10
    assert replayed.cash == pytest.approx(999000.0)


def test_replay_requires_initialization_event():
    engine = TradingEngine.for_paper_trading(
        risk_config=_risk_config(semi_auto=False),
        journal=InMemoryJournal(),
        starting_cash=1_000_000.0,
    )

    with pytest.raises(ValueError, match="PORTFOLIO_INITIALIZED"):
        engine.replay_portfolio([])


def test_paper_flow_supports_partial_fills_and_keeps_open_order_until_complete():
    journal = InMemoryJournal()
    engine = TradingEngine.for_paper_trading(
        risk_config=_risk_config(semi_auto=False),
        journal=journal,
        starting_cash=1_000_000.0,
    )
    signal = _build_signal("signal:partial")

    first = engine.process_signal(
        signal,
        requested_quantity=10,
        execution_price=100.0,
        fill_quantities=[4],
    )

    assert first.order is not None
    assert first.order.status.value == "PARTIALLY_FILLED"
    assert first.order.remaining_quantity == 6
    assert [event.event_type.value for event in journal.read_all()] == [
        "PORTFOLIO_INITIALIZED",
        "SIGNAL_EMITTED",
        "INTENT_CREATED",
        "RISK_APPROVED",
        "INTENT_APPROVED_FOR_EXECUTION",
        "ORDER_SUBMITTED",
        "ORDER_ACCEPTED",
        "ORDER_PARTIALLY_FILLED",
        "FILL_RECORDED",
        "PORTFOLIO_UPDATED",
        "PORTFOLIO_SNAPSHOT",
    ]

    second_signal = _build_signal("signal:partial-second")
    rejected = engine.process_signal(
        second_signal,
        requested_quantity=10,
        execution_price=100.0,
    )

    assert rejected.intent.status.value == "RISK_REJECTED"
    assert "duplicate_open_order" in rejected.risk_decision.reject_reasons

    completed = engine.fill_open_order(
        first.order.order_id,
        fill_quantities=[6],
        execution_price=100.0,
    )
    replayed = engine.replay_portfolio(journal.read_all())

    assert completed.status.value == "FILLED"
    assert replayed.positions["2330.TW"].quantity == 10
    assert replayed.cash == pytest.approx(999000.0)
    assert [
        event.event_type
        for event in journal.read_all()
        if event.event_type in {EventType.ORDER_PARTIALLY_FILLED, EventType.ORDER_FILLED}
    ] == [EventType.ORDER_PARTIALLY_FILLED, EventType.ORDER_FILLED]
