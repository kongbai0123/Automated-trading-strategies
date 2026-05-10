from datetime import datetime

from src.trading.events import EventType, JournalEvent
from src.trading.journal import InMemoryJournal


def test_journal_is_append_only_and_preserves_order():
    journal = InMemoryJournal()
    event_one = JournalEvent(
        event_id="evt:1",
        event_type=EventType.SIGNAL_EMITTED,
        aggregate_id="signal:1",
        payload={"symbol": "2330.TW"},
        created_at=datetime(2026, 5, 7, 9, 0, 1),
        market_time=datetime(2026, 5, 7, 9, 0, 0),
        processed_at=datetime(2026, 5, 7, 9, 0, 2),
    )
    event_two = JournalEvent(
        event_id="evt:2",
        event_type=EventType.ORDER_FILLED,
        aggregate_id="order:1",
        payload={"quantity": 100},
        created_at=datetime(2026, 5, 7, 9, 1, 1),
        market_time=datetime(2026, 5, 7, 9, 1, 0),
        processed_at=datetime(2026, 5, 7, 9, 1, 2),
    )

    journal.append(event_one)
    journal.append(event_two)

    replay = journal.read_all()
    assert [item.event_id for item in replay] == ["evt:1", "evt:2"]

    replay.append(event_one)

    assert len(journal.read_all()) == 2
