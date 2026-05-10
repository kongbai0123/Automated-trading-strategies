from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


def generate_trace_id(prefix: str, *parts: str) -> str:
    normalized = ":".join(str(part) for part in parts)
    return f"{prefix}:{normalized}"


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class IntentStatus(str, Enum):
    PENDING_RISK_CHECK = "PENDING_RISK_CHECK"
    RISK_APPROVED = "RISK_APPROVED"
    RISK_REJECTED = "RISK_REJECTED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED_FOR_EXECUTION = "APPROVED_FOR_EXECUTION"
    EXPIRED = "EXPIRED"


class OrderStatus(str, Enum):
    NEW = "NEW"
    ACCEPTED = "ACCEPTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class DecisionStatus(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    APPROVED_WITH_WARNINGS = "APPROVED_WITH_WARNINGS"


@dataclass(frozen=True)
class SignalEvent:
    signal_id: str
    run_id: str
    strategy_id: str
    symbol: str
    timeframe: str
    side: OrderSide
    signal_type: str
    strength: float
    confidence: float
    market_time: datetime
    created_at: datetime
    processed_at: datetime
    metadata: dict[str, Any]


@dataclass(frozen=True)
class OrderIntent:
    intent_id: str
    signal_id: str
    run_id: str
    strategy_id: str
    symbol: str
    timeframe: str
    side: OrderSide
    quantity_policy: str
    requested_quantity: int
    order_type: str
    limit_price: float | None
    stop_price: float | None
    reason: str
    status: IntentStatus
    expires_at: datetime
    market_time: datetime
    created_at: datetime
    processed_at: datetime
    metadata: dict[str, Any]

    @classmethod
    def from_signal(
        cls,
        signal: SignalEvent,
        intent_id: str,
        quantity_policy: str,
        requested_quantity: int,
        order_type: str,
        reason: str,
        expires_at: datetime,
    ) -> "OrderIntent":
        return cls(
            intent_id=intent_id,
            signal_id=signal.signal_id,
            run_id=signal.run_id,
            strategy_id=signal.strategy_id,
            symbol=signal.symbol,
            timeframe=signal.timeframe,
            side=signal.side,
            quantity_policy=quantity_policy,
            requested_quantity=requested_quantity,
            order_type=order_type,
            limit_price=None,
            stop_price=None,
            reason=reason,
            status=IntentStatus.PENDING_RISK_CHECK,
            expires_at=expires_at,
            market_time=signal.market_time,
            created_at=signal.created_at,
            processed_at=signal.processed_at,
            metadata={"signal_type": signal.signal_type},
        )


@dataclass(frozen=True)
class FillEvent:
    fill_id: str
    order_id: str
    symbol: str
    side: OrderSide
    fill_quantity: int
    fill_price: float
    commission: float
    slippage: float
    filled_at: datetime
    market_time: datetime
    processed_at: datetime


@dataclass(frozen=True)
class PositionState:
    symbol: str
    quantity: int
    average_price: float


@dataclass(frozen=True)
class PortfolioState:
    cash: float
    positions: dict[str, PositionState]
    realized_pnl: float
    unrealized_pnl: float
    equity: float
    gross_exposure: float

    @classmethod
    def initial(cls, cash: float) -> "PortfolioState":
        return cls(
            cash=cash,
            positions={},
            realized_pnl=0.0,
            unrealized_pnl=0.0,
            equity=cash,
            gross_exposure=0.0,
        )


@dataclass(frozen=True)
class RiskDecision:
    risk_decision_id: str
    intent_id: str
    approved: bool
    decision_status: DecisionStatus
    reject_reasons: list[str]
    warning_reasons: list[str]
    adjusted_quantity: int
    risk_score: float
    constraints_checked: list[str]
    created_at: datetime
    processed_at: datetime

    @property
    def reasons(self) -> list[str]:
        return self.reject_reasons + self.warning_reasons


@dataclass(frozen=True)
class OrderRequest:
    order_id: str
    intent_id: str
    symbol: str
    side: OrderSide
    order_type: str
    quantity: int
    market_time: datetime
    submitted_at: datetime
    processed_at: datetime


@dataclass(frozen=True)
class Order:
    order_id: str
    intent_id: str
    symbol: str
    side: OrderSide
    order_type: str
    quantity: int
    filled_quantity: int
    remaining_quantity: int
    status: OrderStatus
    submitted_at: datetime
    market_time: datetime
    processed_at: datetime


@dataclass(frozen=True)
class BrokerPosition:
    symbol: str
    quantity: int
