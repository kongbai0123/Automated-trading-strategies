from datetime import datetime

from src.trading.models import (
    IntentStatus,
    OrderIntent,
    OrderSide,
    SignalEvent,
    generate_trace_id,
)


def test_signal_and_intent_keep_traceable_ids_and_timestamps():
    market_time = datetime(2026, 5, 7, 9, 0, 0)
    created_at = datetime(2026, 5, 7, 9, 0, 1)
    processed_at = datetime(2026, 5, 7, 9, 0, 2)

    signal = SignalEvent(
        signal_id=generate_trace_id(
            "signal", "run-1", "2330.TW", market_time.isoformat()
        ),
        run_id="run-1",
        strategy_id="ma-cross",
        symbol="2330.TW",
        timeframe="1d",
        side=OrderSide.BUY,
        signal_type="ENTRY",
        strength=0.8,
        confidence=0.7,
        market_time=market_time,
        created_at=created_at,
        processed_at=processed_at,
        metadata={"source": "test"},
    )

    intent = OrderIntent.from_signal(
        signal=signal,
        intent_id=generate_trace_id("intent", signal.signal_id, "market"),
        quantity_policy="fixed_units",
        requested_quantity=100,
        order_type="MARKET",
        reason="signal approved for intent creation",
        expires_at=datetime(2026, 5, 8, 9, 0, 0),
    )

    assert signal.signal_id.startswith("signal:")
    assert intent.intent_id.startswith("intent:")
    assert intent.signal_id == signal.signal_id
    assert intent.status is IntentStatus.PENDING_RISK_CHECK
    assert intent.market_time == market_time
    assert intent.created_at == created_at
    assert intent.processed_at == processed_at
