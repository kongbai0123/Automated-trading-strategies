from __future__ import annotations

from datetime import datetime

from src.trading.events import EventType, JournalEvent
from src.trading.models import PortfolioState, PositionState
from src.ui.components.trade_lifecycle_panel import build_lifecycle_snapshot


def _event(event_type: EventType, aggregate_id: str, payload: dict[str, object], minute: int) -> JournalEvent:
    timestamp = datetime(2026, 5, 10, 9, minute, 0)
    return JournalEvent(
        event_id=f"evt:{aggregate_id}:{event_type.value}",
        event_type=event_type,
        aggregate_id=aggregate_id,
        payload=payload,
        created_at=timestamp,
        market_time=timestamp,
        processed_at=timestamp,
    )


def test_lifecycle_snapshot_exposes_trading_workflow_state() -> None:
    events = [
        _event(EventType.SIGNAL_EMITTED, "signal:1", {"symbol": "2330.TW"}, 0),
        _event(
            EventType.INTENT_CREATED,
            "intent:1",
            {"signal_id": "signal:1", "requested_quantity": 10},
            1,
        ),
        _event(
            EventType.RISK_APPROVED,
            "intent:1",
            {
                "risk_decision_id": "risk:1",
                "decision_status": "APPROVED",
                "reject_reasons": [],
                "warning_reasons": [],
            },
            2,
        ),
        _event(EventType.INTENT_APPROVED_FOR_EXECUTION, "intent:1", {"signal_id": "signal:1"}, 3),
        _event(EventType.ORDER_SUBMITTED, "order:1", {"intent_id": "intent:1"}, 4),
        _event(EventType.ORDER_ACCEPTED, "order:1", {"intent_id": "intent:1"}, 5),
        _event(
            EventType.FILL_RECORDED,
            "order:1",
            {
                "fill_id": "fill:1",
                "order_id": "order:1",
                "symbol": "2330.TW",
                "side": "BUY",
                "fill_quantity": 10,
                "fill_price": 100.0,
                "commission": 0.0,
                "slippage": 0.0,
                "filled_at": datetime(2026, 5, 10, 9, 6, 0),
                "market_time": datetime(2026, 5, 10, 9, 6, 0),
                "processed_at": datetime(2026, 5, 10, 9, 6, 0),
            },
            6,
        ),
        _event(
            EventType.PORTFOLIO_SNAPSHOT,
            "portfolio:main",
            {"cash": 999000.0, "gross_exposure": 1000.0, "equity": 1000000.0},
            7,
        ),
    ]
    portfolio_state = PortfolioState(
        cash=999000.0,
        positions={"2330.TW": PositionState(symbol="2330.TW", quantity=10, average_price=100.0)},
        realized_pnl=0.0,
        unrealized_pnl=0.0,
        equity=1000000.0,
        gross_exposure=1000.0,
    )

    snapshot = build_lifecycle_snapshot(events, portfolio_state=portfolio_state)

    assert snapshot.latest_signal["signal_id"] == "signal:1"
    assert snapshot.latest_intent["intent_id"] == "intent:1"
    assert snapshot.latest_intent["status"] == "APPROVED_FOR_EXECUTION"
    assert snapshot.latest_risk["status"] == "APPROVED"
    assert snapshot.latest_order["order_id"] == "order:1"
    assert snapshot.latest_order["status"] == "ACCEPTED"
    assert snapshot.current_positions == [
        {"symbol": "2330.TW", "quantity": 10, "average_price": 100.0}
    ]
    assert snapshot.recent_fills[0]["fill_id"] == "fill:1"
    assert snapshot.timeline_rows[-1]["phase"] == "PORTFOLIO_SNAPSHOT"


def test_lifecycle_snapshot_marks_rejected_intent_without_order() -> None:
    events = [
        _event(EventType.SIGNAL_EMITTED, "signal:2", {"symbol": "NVDA"}, 0),
        _event(
            EventType.INTENT_CREATED,
            "intent:2",
            {"signal_id": "signal:2", "requested_quantity": 5},
            1,
        ),
        _event(
            EventType.RISK_REJECTED,
            "intent:2",
            {
                "risk_decision_id": "risk:2",
                "decision_status": "REJECTED",
                "reject_reasons": ["cash_constraint"],
                "warning_reasons": [],
            },
            2,
        ),
    ]

    snapshot = build_lifecycle_snapshot(events)

    assert snapshot.latest_intent["status"] == "RISK_REJECTED"
    assert snapshot.latest_risk["reject_reasons"] == ["cash_constraint"]
    assert snapshot.latest_order is None
    assert snapshot.open_orders == []
