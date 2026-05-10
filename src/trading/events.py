from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class EventType(str, Enum):
    PORTFOLIO_INITIALIZED = "PORTFOLIO_INITIALIZED"
    SIGNAL_EMITTED = "SIGNAL_EMITTED"
    INTENT_CREATED = "INTENT_CREATED"
    RISK_APPROVED = "RISK_APPROVED"
    RISK_REJECTED = "RISK_REJECTED"
    INTENT_PENDING_APPROVAL = "INTENT_PENDING_APPROVAL"
    INTENT_APPROVED_FOR_EXECUTION = "INTENT_APPROVED_FOR_EXECUTION"
    ORDER_SUBMITTED = "ORDER_SUBMITTED"
    ORDER_ACCEPTED = "ORDER_ACCEPTED"
    ORDER_PARTIALLY_FILLED = "ORDER_PARTIALLY_FILLED"
    ORDER_FILLED = "ORDER_FILLED"
    ORDER_REJECTED = "ORDER_REJECTED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    FILL_RECORDED = "FILL_RECORDED"
    PORTFOLIO_UPDATED = "PORTFOLIO_UPDATED"
    PORTFOLIO_SNAPSHOT = "PORTFOLIO_SNAPSHOT"


@dataclass(frozen=True)
class JournalEvent:
    event_id: str
    event_type: EventType
    aggregate_id: str
    payload: dict[str, Any]
    created_at: datetime
    market_time: datetime
    processed_at: datetime
