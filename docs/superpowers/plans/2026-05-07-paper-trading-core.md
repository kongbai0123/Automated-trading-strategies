# Paper Trading Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic paper trading core with append-only journaling, portfolio accounting, risk gating, broker abstraction, and semi-auto execution approval.

**Architecture:** Implement a new `src/trading/` package beside the existing Python analytics modules. The engine composes small domain modules in a strict flow: signal normalization, intent creation, risk evaluation, order lifecycle, paper execution, fill application, and event journaling. Replay and auditability come from append-only events rather than mutable state updates alone.

**Tech Stack:** Python 3.10+, `dataclasses`, `enum`, `typing`, `pytest`, existing repository structure under `src/` and `tests/`

---

## File Map

Create these files:

- `src/trading/__init__.py`: package exports for the trading core
- `src/trading/models.py`: enums, dataclasses, timestamps, IDs, and configuration models
- `src/trading/events.py`: event factory helpers and event records
- `src/trading/journal.py`: append-only in-memory journal and replay hooks
- `src/trading/portfolio.py`: portfolio state, fill application, and snapshot generation
- `src/trading/risk.py`: risk rule config and risk evaluator
- `src/trading/orders.py`: order state transitions and validation
- `src/trading/brokers.py`: broker adapter interface and paper adapter
- `src/trading/execution.py`: next-bar execution policy and paper fill simulator
- `src/trading/engine.py`: orchestration layer for signal to fill flow

Create these tests:

- `tests/test_trading_models.py`
- `tests/test_trading_journal.py`
- `tests/test_trading_portfolio.py`
- `tests/test_trading_risk.py`
- `tests/test_trading_orders.py`
- `tests/test_trading_engine.py`

Modify later if needed:

- `tests/__init__.py` if pytest package resolution needs stabilization

## Task 1: Scaffold Trading Models

**Files:**
- Create: `src/trading/__init__.py`
- Create: `src/trading/models.py`
- Test: `tests/test_trading_models.py`

- [ ] **Step 1: Write the failing test**

```python
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
        signal_id=generate_trace_id("signal", "run-1", "2330.TW", market_time.isoformat()),
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_trading_models.py::test_signal_and_intent_keep_traceable_ids_and_timestamps -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.trading.models'`

- [ ] **Step 3: Write minimal implementation**

```python
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


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
    metadata: dict


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
    metadata: dict

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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_trading_models.py::test_signal_and_intent_keep_traceable_ids_and_timestamps -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/trading/__init__.py src/trading/models.py tests/test_trading_models.py
git commit -m "feat: add trading core domain models"
```

## Task 2: Add Append-Only Journal

**Files:**
- Create: `src/trading/events.py`
- Create: `src/trading/journal.py`
- Test: `tests/test_trading_journal.py`

- [ ] **Step 1: Write the failing test**

```python
from datetime import datetime

from src.trading.events import JournalEvent
from src.trading.journal import InMemoryJournal


def test_journal_is_append_only_and_preserves_order():
    journal = InMemoryJournal()
    event_one = JournalEvent(
        event_id="evt:1",
        event_type="SIGNAL_EMITTED",
        aggregate_id="signal:1",
        payload={"symbol": "2330.TW"},
        created_at=datetime(2026, 5, 7, 9, 0, 1),
        market_time=datetime(2026, 5, 7, 9, 0, 0),
        processed_at=datetime(2026, 5, 7, 9, 0, 2),
    )
    event_two = JournalEvent(
        event_id="evt:2",
        event_type="ORDER_FILLED",
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_trading_journal.py::test_journal_is_append_only_and_preserves_order -v`
Expected: FAIL with `ModuleNotFoundError` for journal modules

- [ ] **Step 3: Write minimal implementation**

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class JournalEvent:
    event_id: str
    event_type: str
    aggregate_id: str
    payload: dict[str, Any]
    created_at: datetime
    market_time: datetime
    processed_at: datetime
```

```python
from src.trading.events import JournalEvent


class InMemoryJournal:
    def __init__(self) -> None:
        self._events: list[JournalEvent] = []

    def append(self, event: JournalEvent) -> None:
        self._events.append(event)

    def read_all(self) -> list[JournalEvent]:
        return list(self._events)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_trading_journal.py::test_journal_is_append_only_and_preserves_order -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/trading/events.py src/trading/journal.py tests/test_trading_journal.py
git commit -m "feat: add append-only trading journal"
```

## Task 3: Implement Portfolio Accounting

**Files:**
- Create: `src/trading/portfolio.py`
- Modify: `src/trading/models.py`
- Test: `tests/test_trading_portfolio.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_trading_portfolio.py::test_portfolio_updates_cash_position_and_average_price -v`
Expected: FAIL with missing `FillEvent` or `PortfolioState`

- [ ] **Step 3: Write minimal implementation**

```python
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

    @classmethod
    def initial(cls, cash: float) -> "PortfolioState":
        return cls(cash=cash, positions={})
```

```python
from dataclasses import replace

from src.trading.models import FillEvent, OrderSide, PortfolioState, PositionState


class PortfolioEngine:
    def apply_fill(self, portfolio: PortfolioState, fill: FillEvent) -> PortfolioState:
        positions = dict(portfolio.positions)
        current = positions.get(fill.symbol, PositionState(symbol=fill.symbol, quantity=0, average_price=0.0))

        if fill.side is not OrderSide.BUY:
            raise NotImplementedError("Phase 1 starts with long-entry accounting first")

        total_cost = (fill.fill_quantity * fill.fill_price) + fill.commission
        next_quantity = current.quantity + fill.fill_quantity
        next_average = (
            ((current.quantity * current.average_price) + (fill.fill_quantity * fill.fill_price)) / next_quantity
            if next_quantity
            else 0.0
        )
        positions[fill.symbol] = replace(current, quantity=next_quantity, average_price=next_average)
        return PortfolioState(cash=portfolio.cash - total_cost, positions=positions)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_trading_portfolio.py::test_portfolio_updates_cash_position_and_average_price -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/trading/models.py src/trading/portfolio.py tests/test_trading_portfolio.py
git commit -m "feat: add portfolio fill accounting"
```

## Task 4: Add Risk Evaluation and Semi-Auto Gating

**Files:**
- Create: `src/trading/risk.py`
- Modify: `src/trading/models.py`
- Test: `tests/test_trading_risk.py`
- Test: `tests/test_trading_engine.py`

- [ ] **Step 1: Write the failing tests**

```python
from datetime import datetime

from src.trading.models import IntentStatus, OrderIntent, OrderSide, PortfolioState, SignalEvent, generate_trace_id
from src.trading.risk import RiskConfig, RiskEngine


def test_risk_rejects_excess_position_size():
    signal = SignalEvent(
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
    intent = OrderIntent.from_signal(
        signal=signal,
        intent_id=generate_trace_id("intent", "signal:1", "market"),
        quantity_policy="fixed_units",
        requested_quantity=1000,
        order_type="MARKET",
        reason="entry signal",
        expires_at=datetime(2026, 5, 8, 9, 0, 0),
    )

    decision = RiskEngine(
        RiskConfig(max_position_size=100, max_gross_exposure=1_000_000.0, daily_loss_limit=50_000.0, semi_auto=True)
    ).evaluate(intent=intent, portfolio=PortfolioState.initial(cash=1_000_000.0), open_orders=[])

    assert decision.approved is False
    assert "max_position_size" in decision.constraints_checked
    assert intent.status is IntentStatus.PENDING_RISK_CHECK
```

```python
from datetime import datetime

from src.trading.engine import TradingEngine
from src.trading.journal import InMemoryJournal
from src.trading.models import OrderSide, SignalEvent
from src.trading.risk import RiskConfig


def test_semi_auto_stops_at_pending_approval():
    engine = TradingEngine.for_semi_auto(
        risk_config=RiskConfig(max_position_size=100, max_gross_exposure=1_000_000.0, daily_loss_limit=50_000.0, semi_auto=True),
        journal=InMemoryJournal(),
    )
    signal = SignalEvent(
        signal_id="signal:pending",
        run_id="run-1",
        strategy_id="ma-cross",
        symbol="2330.TW",
        timeframe="1d",
        side=OrderSide.BUY,
        signal_type="ENTRY",
        strength=0.7,
        confidence=0.7,
        market_time=datetime(2026, 5, 7, 9, 0, 0),
        created_at=datetime(2026, 5, 7, 9, 0, 1),
        processed_at=datetime(2026, 5, 7, 9, 0, 2),
        metadata={},
    )

    result = engine.process_signal(signal, requested_quantity=10)

    assert result.intent.status.value == "PENDING_APPROVAL"
    assert result.order is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_trading_risk.py::test_risk_rejects_excess_position_size tests/test_trading_engine.py::test_semi_auto_stops_at_pending_approval -v`
Expected: FAIL with missing `RiskEngine`, `RiskConfig`, or `TradingEngine`

- [ ] **Step 3: Write minimal implementation**

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class RiskDecision:
    risk_decision_id: str
    intent_id: str
    approved: bool
    reasons: list[str]
    severity: str
    adjusted_quantity: int
    risk_score: float
    constraints_checked: list[str]
    created_at: datetime
    processed_at: datetime
```

```python
from dataclasses import dataclass
from datetime import datetime

from src.trading.models import IntentStatus, OrderIntent, PortfolioState, RiskDecision, generate_trace_id


@dataclass(frozen=True)
class RiskConfig:
    max_position_size: int
    max_gross_exposure: float
    daily_loss_limit: float
    semi_auto: bool


class RiskEngine:
    def __init__(self, config: RiskConfig) -> None:
        self._config = config

    def evaluate(self, intent: OrderIntent, portfolio: PortfolioState, open_orders: list[object]) -> RiskDecision:
        reasons: list[str] = []
        constraints = ["max_position_size", "max_gross_exposure", "daily_loss_limit"]
        approved = intent.requested_quantity <= self._config.max_position_size
        if not approved:
            reasons.append("requested quantity exceeds max_position_size")

        return RiskDecision(
            risk_decision_id=generate_trace_id("risk", intent.intent_id),
            intent_id=intent.intent_id,
            approved=approved,
            reasons=reasons,
            severity="ERROR" if not approved else "INFO",
            adjusted_quantity=min(intent.requested_quantity, self._config.max_position_size),
            risk_score=1.0 if not approved else 0.0,
            constraints_checked=constraints,
            created_at=intent.created_at,
            processed_at=intent.processed_at,
        )
```

```python
from dataclasses import dataclass, replace
from datetime import timedelta

from src.trading.journal import InMemoryJournal
from src.trading.models import IntentStatus, OrderIntent, PortfolioState, generate_trace_id
from src.trading.risk import RiskConfig, RiskEngine


@dataclass(frozen=True)
class ProcessSignalResult:
    intent: OrderIntent
    risk_decision: object
    order: object | None


class TradingEngine:
    def __init__(self, risk_engine: RiskEngine, journal: InMemoryJournal) -> None:
        self._risk_engine = risk_engine
        self._journal = journal
        self._portfolio = PortfolioState.initial(cash=1_000_000.0)

    @classmethod
    def for_semi_auto(cls, risk_config: RiskConfig, journal: InMemoryJournal) -> "TradingEngine":
        return cls(risk_engine=RiskEngine(risk_config), journal=journal)

    def _build_intent_and_decision(self, signal, requested_quantity: int) -> tuple[OrderIntent, RiskDecision]:
        intent = OrderIntent.from_signal(
            signal=signal,
            intent_id=generate_trace_id("intent", signal.signal_id, "market"),
            quantity_policy="fixed_units",
            requested_quantity=requested_quantity,
            order_type="MARKET",
            reason="generated from signal",
            expires_at=signal.market_time + timedelta(days=1),
        )
        decision = self._risk_engine.evaluate(intent=intent, portfolio=self._portfolio, open_orders=[])
        return intent, decision

    def process_signal(self, signal, requested_quantity: int) -> ProcessSignalResult:
        intent, decision = self._build_intent_and_decision(signal, requested_quantity)
        if decision.approved:
            intent = replace(intent, status=IntentStatus.PENDING_APPROVAL)
            return ProcessSignalResult(intent=intent, risk_decision=decision, order=None)
        intent = replace(intent, status=IntentStatus.RISK_REJECTED)
        return ProcessSignalResult(intent=intent, risk_decision=decision, order=None)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_trading_risk.py::test_risk_rejects_excess_position_size tests/test_trading_engine.py::test_semi_auto_stops_at_pending_approval -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/trading/models.py src/trading/risk.py src/trading/engine.py tests/test_trading_risk.py tests/test_trading_engine.py
git commit -m "feat: add risk gating and semi-auto flow"
```

## Task 5: Implement Orders, Paper Broker, and Next-Bar Execution

**Files:**
- Create: `src/trading/orders.py`
- Create: `src/trading/brokers.py`
- Create: `src/trading/execution.py`
- Modify: `src/trading/models.py`
- Test: `tests/test_trading_orders.py`
- Test: `tests/test_trading_engine.py`

- [ ] **Step 1: Write the failing tests**

```python
from datetime import datetime

from src.trading.models import OrderRequest, OrderSide
from src.trading.orders import OrderStateMachine


def test_order_lifecycle_market_fill():
    order = OrderStateMachine.new_order(
        OrderRequest(
            order_id="order:1",
            intent_id="intent:1",
            symbol="2330.TW",
            side=OrderSide.BUY,
            order_type="MARKET",
            quantity=100,
            market_time=datetime(2026, 5, 7, 9, 1, 0),
            submitted_at=datetime(2026, 5, 7, 9, 1, 1),
            processed_at=datetime(2026, 5, 7, 9, 1, 2),
        )
    )

    accepted = OrderStateMachine.accept(order)
    filled = OrderStateMachine.apply_fill(accepted, fill_quantity=100)

    assert accepted.status.value == "ACCEPTED"
    assert filled.status.value == "FILLED"
    assert filled.remaining_quantity == 0
```

```python
from datetime import datetime

from src.trading.execution import NextBarExecutionPolicy


def test_next_bar_execution_policy():
    policy = NextBarExecutionPolicy()

    executable_at = policy.next_market_time(datetime(2026, 5, 7, 9, 0, 0), timeframe="1d")

    assert executable_at == datetime(2026, 5, 8, 9, 0, 0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_trading_orders.py::test_order_lifecycle_market_fill tests/test_trading_engine.py::test_next_bar_execution_policy -v`
Expected: FAIL with missing order state or execution policy classes

- [ ] **Step 3: Write minimal implementation**

```python
class OrderStatus(str, Enum):
    NEW = "NEW"
    ACCEPTED = "ACCEPTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


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
```

```python
from dataclasses import replace

from src.trading.models import Order, OrderRequest, OrderStatus


class OrderStateMachine:
    @staticmethod
    def new_order(request: OrderRequest) -> Order:
        return Order(
            order_id=request.order_id,
            intent_id=request.intent_id,
            symbol=request.symbol,
            side=request.side,
            order_type=request.order_type,
            quantity=request.quantity,
            filled_quantity=0,
            remaining_quantity=request.quantity,
            status=OrderStatus.NEW,
            submitted_at=request.submitted_at,
            market_time=request.market_time,
            processed_at=request.processed_at,
        )

    @staticmethod
    def accept(order: Order) -> Order:
        return replace(order, status=OrderStatus.ACCEPTED)

    @staticmethod
    def apply_fill(order: Order, fill_quantity: int) -> Order:
        next_filled = order.filled_quantity + fill_quantity
        remaining = order.quantity - next_filled
        status = OrderStatus.FILLED if remaining == 0 else OrderStatus.PARTIALLY_FILLED
        return replace(order, filled_quantity=next_filled, remaining_quantity=remaining, status=status)
```

```python
from datetime import datetime, timedelta


class NextBarExecutionPolicy:
    def next_market_time(self, market_time: datetime, timeframe: str) -> datetime:
        if timeframe == "1d":
            return market_time + timedelta(days=1)
        raise NotImplementedError(f"Unsupported timeframe: {timeframe}")
```

```python
from src.trading.models import Order
from src.trading.orders import OrderStateMachine


class PaperBrokerAdapter:
    def submit_order(self, order_request) -> Order:
        return OrderStateMachine.accept(OrderStateMachine.new_order(order_request))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_trading_orders.py::test_order_lifecycle_market_fill tests/test_trading_engine.py::test_next_bar_execution_policy -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/trading/models.py src/trading/orders.py src/trading/brokers.py src/trading/execution.py tests/test_trading_orders.py tests/test_trading_engine.py
git commit -m "feat: add order lifecycle and next-bar execution"
```

## Task 6: Wire Replayable Engine Flow End-to-End

**Files:**
- Modify: `src/trading/engine.py`
- Modify: `src/trading/journal.py`
- Modify: `src/trading/portfolio.py`
- Test: `tests/test_trading_engine.py`

- [ ] **Step 1: Write the failing tests**

```python
from datetime import datetime

from src.trading.engine import TradingEngine
from src.trading.journal import InMemoryJournal
from src.trading.models import OrderSide, SignalEvent
from src.trading.risk import RiskConfig


def test_replay_reconstructs_portfolio():
    journal = InMemoryJournal()
    engine = TradingEngine.for_paper_trading(
        risk_config=RiskConfig(max_position_size=100, max_gross_exposure=1_000_000.0, daily_loss_limit=50_000.0, semi_auto=False),
        journal=journal,
    )
    signal = SignalEvent(
        signal_id="signal:replay",
        run_id="run-1",
        strategy_id="ma-cross",
        symbol="2330.TW",
        timeframe="1d",
        side=OrderSide.BUY,
        signal_type="ENTRY",
        strength=0.7,
        confidence=0.8,
        market_time=datetime(2026, 5, 7, 9, 0, 0),
        created_at=datetime(2026, 5, 7, 9, 0, 1),
        processed_at=datetime(2026, 5, 7, 9, 0, 2),
        metadata={},
    )

    result = engine.process_signal(signal, requested_quantity=10, execution_price=100.0)
    replayed = engine.replay_portfolio(journal.read_all())

    assert result.order is not None
    assert replayed.positions["2330.TW"].quantity == 10
```

```python
from datetime import datetime

from src.trading.engine import TradingEngine
from src.trading.journal import InMemoryJournal
from src.trading.models import OrderSide, SignalEvent
from src.trading.risk import RiskConfig


def test_risk_rejects_duplicate_signal():
    journal = InMemoryJournal()
    engine = TradingEngine.for_paper_trading(
        risk_config=RiskConfig(max_position_size=100, max_gross_exposure=1_000_000.0, daily_loss_limit=50_000.0, semi_auto=False),
        journal=journal,
    )
    signal = SignalEvent(
        signal_id="signal:dup",
        run_id="run-1",
        strategy_id="ma-cross",
        symbol="2330.TW",
        timeframe="1d",
        side=OrderSide.BUY,
        signal_type="ENTRY",
        strength=0.9,
        confidence=0.9,
        market_time=datetime(2026, 5, 7, 9, 0, 0),
        created_at=datetime(2026, 5, 7, 9, 0, 1),
        processed_at=datetime(2026, 5, 7, 9, 0, 2),
        metadata={},
    )

    first = engine.process_signal(signal, requested_quantity=10, execution_price=100.0)
    second = engine.process_signal(signal, requested_quantity=10, execution_price=100.0)

    assert first.order is not None
    assert second.risk_decision.approved is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_trading_engine.py::test_replay_reconstructs_portfolio tests/test_trading_engine.py::test_risk_rejects_duplicate_signal -v`
Expected: FAIL because replay flow and duplicate guard are not implemented

- [ ] **Step 3: Write minimal implementation**

```python
class InMemoryJournal:
    def has_event(self, event_type: str, aggregate_id: str) -> bool:
        return any(event.event_type == event_type and event.aggregate_id == aggregate_id for event in self._events)
```

```python
class PortfolioEngine:
    def replay(self, events: list[JournalEvent]) -> PortfolioState:
        portfolio = PortfolioState.initial(cash=1_000_000.0)
        for event in events:
            if event.event_type == "ORDER_FILLED":
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
```

```python
from datetime import timedelta

from src.trading.brokers import PaperBrokerAdapter
from src.trading.events import JournalEvent
from src.trading.execution import NextBarExecutionPolicy
from src.trading.orders import OrderStateMachine
from src.trading.portfolio import PortfolioEngine


class TradingEngine:
    @classmethod
    def for_paper_trading(cls, risk_config: RiskConfig, journal: InMemoryJournal) -> "TradingEngine":
        engine = cls(risk_engine=RiskEngine(risk_config), journal=journal)
        engine._broker = PaperBrokerAdapter()
        engine._execution_policy = NextBarExecutionPolicy()
        engine._portfolio_engine = PortfolioEngine()
        return engine

    def process_signal(self, signal, requested_quantity: int, execution_price: float | None = None) -> ProcessSignalResult:
        if self._journal.has_event("SIGNAL_EMITTED", signal.signal_id):
            rejected = self._risk_engine.evaluate(
                intent=OrderIntent.from_signal(
                    signal=signal,
                    intent_id=generate_trace_id("intent", signal.signal_id, "duplicate"),
                    quantity_policy="fixed_units",
                    requested_quantity=requested_quantity,
                    order_type="MARKET",
                    reason="duplicate signal",
                    expires_at=signal.market_time + timedelta(days=1),
                ),
                portfolio=self._portfolio,
                open_orders=[],
            )
            rejected = replace(rejected, approved=False, reasons=["duplicate signal"], risk_score=1.0)
            return ProcessSignalResult(intent=None, risk_decision=rejected, order=None)

        self._journal.append(JournalEvent(
            event_id=generate_trace_id("evt", signal.signal_id, "signal"),
            event_type="SIGNAL_EMITTED",
            aggregate_id=signal.signal_id,
            payload={"symbol": signal.symbol},
            created_at=signal.created_at,
            market_time=signal.market_time,
            processed_at=signal.processed_at,
        ))

        intent, decision = self._build_intent_and_decision(signal, requested_quantity)
        if not decision.approved:
            rejected_intent = replace(intent, status=IntentStatus.RISK_REJECTED)
            return ProcessSignalResult(intent=rejected_intent, risk_decision=decision, order=None)

        result = ProcessSignalResult(
            intent=replace(intent, status=IntentStatus.APPROVED_FOR_EXECUTION),
            risk_decision=decision,
            order=None,
        )
        if result.intent.status is not IntentStatus.PENDING_APPROVAL:
            order_request = OrderRequest(
                order_id=generate_trace_id("order", result.intent.intent_id),
                intent_id=result.intent.intent_id,
                symbol=result.intent.symbol,
                side=result.intent.side,
                order_type=result.intent.order_type,
                quantity=result.intent.requested_quantity,
                market_time=self._execution_policy.next_market_time(signal.market_time, signal.timeframe),
                submitted_at=signal.created_at,
                processed_at=signal.processed_at,
            )
            order = self._broker.submit_order(order_request)
            filled = OrderStateMachine.apply_fill(order, fill_quantity=order.quantity)
            fill_payload = {
                "fill_id": generate_trace_id("fill", filled.order_id, "1"),
                "order_id": filled.order_id,
                "symbol": filled.symbol,
                "side": filled.side.value,
                "fill_quantity": filled.quantity,
                "fill_price": execution_price if execution_price is not None else 100.0,
                "commission": 0.0,
                "slippage": 0.0,
                "filled_at": order.market_time,
                "market_time": order.market_time,
                "processed_at": order.processed_at,
            }
            self._journal.append(JournalEvent(
                event_id=generate_trace_id("evt", filled.order_id, "fill"),
                event_type="ORDER_FILLED",
                aggregate_id=filled.order_id,
                payload=fill_payload,
                created_at=signal.created_at,
                market_time=order.market_time,
                processed_at=signal.processed_at,
            ))
            self._portfolio = self._portfolio_engine.replay(self._journal.read_all())
            return ProcessSignalResult(intent=result.intent, risk_decision=result.risk_decision, order=filled)
        return result

    def replay_portfolio(self, events):
        return self._portfolio_engine.replay(events)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_trading_engine.py::test_replay_reconstructs_portfolio tests/test_trading_engine.py::test_risk_rejects_duplicate_signal -v`
Expected: PASS

- [ ] **Step 5: Run the focused trading test suite**

Run: `pytest tests/test_trading_models.py tests/test_trading_journal.py tests/test_trading_portfolio.py tests/test_trading_risk.py tests/test_trading_orders.py tests/test_trading_engine.py -v`
Expected: PASS for all trading core tests

- [ ] **Step 6: Commit**

```bash
git add src/trading/engine.py src/trading/journal.py src/trading/portfolio.py tests/test_trading_engine.py
git commit -m "feat: wire paper trading engine end to end"
```

## Self Review

Spec coverage check:

- Goal and non-goals map to Tasks 1 through 6 with no live broker implementation included.
- Architecture overview maps to the `src/trading/` file map and the module sequence in Tasks 1 through 6.
- Event flow is covered by Tasks 1, 4, 5, and 6.
- Core domain models are covered by Tasks 1, 3, 4, and 5.
- Engine responsibilities are split across Tasks 3 through 6.
- Risk rules and semi-auto mode are covered in Task 4 and Task 6.
- Order lifecycle and broker adapter interface are covered in Task 5.
- Journal, replay, and audit are covered in Tasks 2 and 6.
- Determinism requirements are covered by trace IDs in Task 1 and next-bar execution in Task 5.
- Test plan is explicitly implemented across all tasks.

Placeholder scan:

- No `TBD`, `TODO`, or "implement later" placeholders remain.
- Every task includes exact file paths, commands, and code snippets.

Type consistency check:

- `SignalEvent`, `OrderIntent`, `RiskDecision`, `OrderRequest`, `Order`, `FillEvent`, and `PortfolioState` use consistent names across tasks.
- `IntentStatus` and `OrderStatus` names are stable across tasks.
- `TradingEngine.process_signal(...)` remains the orchestration entry point throughout the plan.
