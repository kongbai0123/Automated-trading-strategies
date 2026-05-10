from .events import EventType, JournalEvent


class InMemoryJournal:
    def __init__(self) -> None:
        self._events: list[JournalEvent] = []

    def append(self, event: JournalEvent) -> None:
        self._events.append(event)

    def read_all(self) -> list[JournalEvent]:
        return list(self._events)

    def has_event(self, event_type: EventType | str, aggregate_id: str) -> bool:
        target = event_type.value if isinstance(event_type, EventType) else event_type
        return any(
            event.event_type.value == target and event.aggregate_id == aggregate_id
            for event in self._events
        )
