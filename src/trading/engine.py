from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from .brokers import PaperBrokerAdapter
from .events import EventType, JournalEvent
from .execution import NextBarExecutionPolicy
from .journal import InMemoryJournal
from .models import (
    IntentStatus,
    OrderIntent,
    OrderRequest,
    PortfolioState,
    RiskDecision,
    SignalEvent,
    generate_trace_id,
)
from .portfolio import PortfolioEngine
from .risk import RiskConfig, RiskEngine


@dataclass(frozen=True)
class ProcessSignalResult:
    intent: OrderIntent
    risk_decision: RiskDecision
    order: object | None


class TradingEngine:
    def __init__(
        self, risk_engine: RiskEngine, journal: InMemoryJournal, starting_cash: float
    ) -> None:
        self._risk_engine = risk_engine
        self._journal = journal
        self._starting_cash = starting_cash
        self._portfolio = PortfolioState.initial(cash=starting_cash)
        self._broker = None
        self._execution_policy = None
        self._portfolio_engine = PortfolioEngine()

        if not self._journal.has_event(EventType.PORTFOLIO_INITIALIZED, "portfolio:main"):
            self._journal.append(
                JournalEvent(
                    event_id=generate_trace_id("evt", "portfolio:main", "initialized"),
                    event_type=EventType.PORTFOLIO_INITIALIZED,
                    aggregate_id="portfolio:main",
                    payload={"starting_cash": starting_cash},
                    created_at=datetime.min,
                    market_time=datetime.min,
                    processed_at=datetime.min,
                )
            )

    @classmethod
    def for_semi_auto(
        cls,
        risk_config: RiskConfig,
        journal: InMemoryJournal,
        starting_cash: float = 1_000_000.0,
    ) -> "TradingEngine":
        return cls(
            risk_engine=RiskEngine(risk_config),
            journal=journal,
            starting_cash=starting_cash,
        )

    @classmethod
    def for_paper_trading(
        cls,
        risk_config: RiskConfig,
        journal: InMemoryJournal,
        starting_cash: float = 1_000_000.0,
    ) -> "TradingEngine":
        engine = cls(
            risk_engine=RiskEngine(risk_config),
            journal=journal,
            starting_cash=starting_cash,
        )
        engine._broker = PaperBrokerAdapter()
        engine._execution_policy = NextBarExecutionPolicy()
        return engine

    def _seen_signal_ids(self) -> set[str]:
        return {
            event.aggregate_id
            for event in self._journal.read_all()
            if event.event_type is EventType.SIGNAL_EMITTED
        }

    def _last_entry_times(self) -> dict[str, datetime]:
        last_entries: dict[str, datetime] = {}
        for event in self._journal.read_all():
            if event.event_type in {
                EventType.ORDER_PARTIALLY_FILLED,
                EventType.ORDER_FILLED,
                EventType.FILL_RECORDED,
            }:
                symbol = event.payload.get("symbol")
                side = event.payload.get("side")
                if symbol and side == "BUY":
                    last_entries[symbol] = event.market_time
        return last_entries

    def _build_intent_and_decision(
        self, signal: SignalEvent, requested_quantity: int
    ) -> tuple[OrderIntent, RiskDecision]:
        intent = OrderIntent.from_signal(
            signal=signal,
            intent_id=generate_trace_id("intent", signal.signal_id, "market"),
            quantity_policy="fixed_units",
            requested_quantity=requested_quantity,
            order_type="MARKET",
            reason="generated from signal",
            expires_at=signal.market_time + timedelta(days=1),
        )
        open_orders = self._broker.list_open_orders() if self._broker is not None else []
        reference_price = float(signal.metadata.get("reference_price", 1.0))
        decision = self._risk_engine.evaluate(
            intent=intent,
            portfolio=self._portfolio,
            open_orders=open_orders,
            reference_price=reference_price,
            seen_signal_ids=self._seen_signal_ids(),
            last_entry_times=self._last_entry_times(),
        )
        return intent, decision

    def _append_event(
        self,
        *,
        event_id: str,
        event_type: EventType,
        aggregate_id: str,
        payload: dict,
        created_at: datetime,
        market_time: datetime,
        processed_at: datetime,
    ) -> None:
        self._journal.append(
            JournalEvent(
                event_id=event_id,
                event_type=event_type,
                aggregate_id=aggregate_id,
                payload=payload,
                created_at=created_at,
                market_time=market_time,
                processed_at=processed_at,
            )
        )

    def process_signal(
        self,
        signal: SignalEvent,
        requested_quantity: int,
        execution_price: float | None = None,
        fill_quantities: list[int] | None = None,
    ) -> ProcessSignalResult:
        intent, decision = self._build_intent_and_decision(signal, requested_quantity)
        if signal.signal_id not in self._seen_signal_ids():
            self._append_event(
                event_id=generate_trace_id("evt", signal.signal_id, "signal"),
                event_type=EventType.SIGNAL_EMITTED,
                aggregate_id=signal.signal_id,
                payload={"symbol": signal.symbol},
                created_at=signal.created_at,
                market_time=signal.market_time,
                processed_at=signal.processed_at,
            )

        self._append_event(
            event_id=generate_trace_id("evt", intent.intent_id, "intent_created"),
            event_type=EventType.INTENT_CREATED,
            aggregate_id=intent.intent_id,
            payload={
                "signal_id": intent.signal_id,
                "requested_quantity": intent.requested_quantity,
            },
            created_at=intent.created_at,
            market_time=intent.market_time,
            processed_at=intent.processed_at,
        )

        self._append_event(
            event_id=generate_trace_id(
                "evt", decision.risk_decision_id, decision.decision_status.value.lower()
            ),
            event_type=(EventType.RISK_APPROVED if decision.approved else EventType.RISK_REJECTED),
            aggregate_id=intent.intent_id,
            payload={
                "risk_decision_id": decision.risk_decision_id,
                "decision_status": decision.decision_status.value,
                "reject_reasons": decision.reject_reasons,
                "warning_reasons": decision.warning_reasons,
            },
            created_at=decision.created_at,
            market_time=intent.market_time,
            processed_at=decision.processed_at,
        )

        if self._broker is None and decision.approved:
            intent = replace(intent, status=IntentStatus.PENDING_APPROVAL)
            self._append_event(
                event_id=generate_trace_id("evt", intent.intent_id, "pending_approval"),
                event_type=EventType.INTENT_PENDING_APPROVAL,
                aggregate_id=intent.intent_id,
                payload={"signal_id": intent.signal_id},
                created_at=intent.created_at,
                market_time=intent.market_time,
                processed_at=intent.processed_at,
            )
            return ProcessSignalResult(intent=intent, risk_decision=decision, order=None)

        if not decision.approved:
            intent = replace(intent, status=IntentStatus.RISK_REJECTED)
            return ProcessSignalResult(intent=intent, risk_decision=decision, order=None)

        executable_intent = replace(intent, status=IntentStatus.APPROVED_FOR_EXECUTION)
        self._append_event(
            event_id=generate_trace_id(
                "evt", executable_intent.intent_id, "approved_for_execution"
            ),
            event_type=EventType.INTENT_APPROVED_FOR_EXECUTION,
            aggregate_id=executable_intent.intent_id,
            payload={"signal_id": executable_intent.signal_id},
            created_at=executable_intent.created_at,
            market_time=executable_intent.market_time,
            processed_at=executable_intent.processed_at,
        )
        order_request = OrderRequest(
            order_id=generate_trace_id("order", executable_intent.intent_id),
            intent_id=executable_intent.intent_id,
            symbol=executable_intent.symbol,
            side=executable_intent.side,
            order_type=executable_intent.order_type,
            quantity=executable_intent.requested_quantity,
            market_time=self._execution_policy.next_market_time(
                signal.market_time, signal.timeframe
            ),
            submitted_at=signal.created_at,
            processed_at=signal.processed_at,
        )
        self._append_event(
            event_id=generate_trace_id("evt", order_request.order_id, "order_submitted"),
            event_type=EventType.ORDER_SUBMITTED,
            aggregate_id=order_request.order_id,
            payload={"intent_id": order_request.intent_id},
            created_at=signal.created_at,
            market_time=order_request.market_time,
            processed_at=signal.processed_at,
        )

        order = self._broker.submit_order(order_request)
        self._append_event(
            event_id=generate_trace_id("evt", order.order_id, "order_accepted"),
            event_type=EventType.ORDER_ACCEPTED,
            aggregate_id=order.order_id,
            payload={"intent_id": order.intent_id},
            created_at=signal.created_at,
            market_time=order.market_time,
            processed_at=signal.processed_at,
        )

        filled = self._apply_fill_sequence(
            order=order,
            fill_quantities=fill_quantities or [order.quantity],
            execution_price=execution_price,
            created_at=signal.created_at,
            market_time=order.market_time,
            processed_at=signal.processed_at,
        )
        return ProcessSignalResult(intent=executable_intent, risk_decision=decision, order=filled)

    def replay_portfolio(self, events: list[JournalEvent]) -> PortfolioState:
        return self._portfolio_engine.replay(events)

    def fill_open_order(
        self,
        order_id: str,
        *,
        fill_quantities: list[int],
        execution_price: float | None = None,
    ):
        order = self._broker.get_order(order_id)
        return self._apply_fill_sequence(
            order=order,
            fill_quantities=fill_quantities,
            execution_price=execution_price,
            created_at=order.submitted_at,
            market_time=order.market_time,
            processed_at=order.processed_at,
        )

    def _apply_fill_sequence(
        self,
        *,
        order,
        fill_quantities: list[int],
        execution_price: float | None,
        created_at: datetime,
        market_time: datetime,
        processed_at: datetime,
    ):
        current_order = order
        fill_price = execution_price if execution_price is not None else 100.0
        for index, fill_quantity in enumerate(fill_quantities, start=1):
            current_order = self._broker.apply_fill(current_order, fill_quantity=fill_quantity)
            order_event_type = (
                EventType.ORDER_FILLED
                if current_order.status.value == "FILLED"
                else EventType.ORDER_PARTIALLY_FILLED
            )
            payload = {
                "fill_id": generate_trace_id("fill", current_order.order_id, str(index)),
                "order_id": current_order.order_id,
                "symbol": current_order.symbol,
                "side": current_order.side.value,
                "fill_quantity": fill_quantity,
                "fill_price": fill_price,
                "commission": 0.0,
                "slippage": 0.0,
                "filled_at": market_time,
                "market_time": market_time,
                "processed_at": processed_at,
            }
            self._append_event(
                event_id=generate_trace_id("evt", current_order.order_id, "fill", str(index)),
                event_type=order_event_type,
                aggregate_id=current_order.order_id,
                payload=payload,
                created_at=created_at,
                market_time=market_time,
                processed_at=processed_at,
            )
            self._append_event(
                event_id=generate_trace_id(
                    "evt", current_order.order_id, "fill_recorded", str(index)
                ),
                event_type=EventType.FILL_RECORDED,
                aggregate_id=current_order.order_id,
                payload=payload,
                created_at=created_at,
                market_time=market_time,
                processed_at=processed_at,
            )
            self._portfolio = self._portfolio_engine.replay(self._journal.read_all())
            portfolio_payload = {
                "cash": self._portfolio.cash,
                "gross_exposure": self._portfolio.gross_exposure,
                "equity": self._portfolio.equity,
            }
            self._append_event(
                event_id=generate_trace_id(
                    "evt",
                    "portfolio:main",
                    current_order.order_id,
                    "updated",
                    str(index),
                ),
                event_type=EventType.PORTFOLIO_UPDATED,
                aggregate_id="portfolio:main",
                payload=portfolio_payload,
                created_at=created_at,
                market_time=market_time,
                processed_at=processed_at,
            )
            self._append_event(
                event_id=generate_trace_id(
                    "evt",
                    "portfolio:main",
                    current_order.order_id,
                    "snapshot",
                    str(index),
                ),
                event_type=EventType.PORTFOLIO_SNAPSHOT,
                aggregate_id="portfolio:main",
                payload=portfolio_payload,
                created_at=created_at,
                market_time=market_time,
                processed_at=processed_at,
            )
        return current_order
