from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd
import streamlit as st

from src.trading.events import EventType, JournalEvent
from src.trading.models import PortfolioState


@dataclass(frozen=True)
class LifecycleSnapshot:
    latest_signal: dict[str, object] | None
    latest_intent: dict[str, object] | None
    latest_risk: dict[str, object] | None
    latest_order: dict[str, object] | None
    open_orders: list[dict[str, object]]
    recent_fills: list[dict[str, object]]
    current_positions: list[dict[str, object]]
    latest_portfolio: dict[str, object] | None
    timeline_rows: list[dict[str, object]]


def build_lifecycle_snapshot(
    events: Iterable[JournalEvent],
    *,
    portfolio_state: PortfolioState | None = None,
) -> LifecycleSnapshot:
    latest_signal = None
    latest_intent = None
    latest_risk = None
    latest_order = None
    latest_portfolio = None
    timeline_rows: list[dict[str, object]] = []
    open_orders: dict[str, dict[str, object]] = {}
    recent_fills: list[dict[str, object]] = []

    for event in events:
        timeline_rows.append(
            {
                "time": event.market_time,
                "event_type": event.event_type.value,
                "phase": event.event_type.value,
                "aggregate_id": event.aggregate_id,
            }
        )
        if event.event_type is EventType.SIGNAL_EMITTED:
            latest_signal = {
                "signal_id": event.aggregate_id,
                "symbol": event.payload.get("symbol"),
                "market_time": event.market_time,
            }
        elif event.event_type is EventType.INTENT_CREATED:
            latest_intent = {
                "intent_id": event.aggregate_id,
                "signal_id": event.payload.get("signal_id"),
                "requested_quantity": event.payload.get("requested_quantity"),
                "status": "PENDING_RISK_CHECK",
            }
        elif event.event_type in {EventType.RISK_APPROVED, EventType.RISK_REJECTED}:
            latest_risk = {
                "status": event.payload.get("decision_status"),
                "reject_reasons": event.payload.get("reject_reasons", []),
                "warning_reasons": event.payload.get("warning_reasons", []),
            }
            if latest_intent and latest_intent["intent_id"] == event.aggregate_id:
                latest_intent = dict(latest_intent)
                latest_intent["status"] = (
                    "RISK_APPROVED"
                    if event.event_type is EventType.RISK_APPROVED
                    else "RISK_REJECTED"
                )
        elif event.event_type is EventType.INTENT_PENDING_APPROVAL:
            if latest_intent and latest_intent["intent_id"] == event.aggregate_id:
                latest_intent = dict(latest_intent)
                latest_intent["status"] = "PENDING_APPROVAL"
        elif event.event_type is EventType.INTENT_APPROVED_FOR_EXECUTION:
            if latest_intent and latest_intent["intent_id"] == event.aggregate_id:
                latest_intent = dict(latest_intent)
                latest_intent["status"] = "APPROVED_FOR_EXECUTION"
        elif event.event_type in {EventType.ORDER_SUBMITTED, EventType.ORDER_ACCEPTED, EventType.ORDER_PARTIALLY_FILLED, EventType.ORDER_FILLED, EventType.ORDER_CANCELLED, EventType.ORDER_REJECTED}:
            latest_order = {
                "order_id": event.aggregate_id,
                "status": event.event_type.value.removeprefix("ORDER_"),
                "intent_id": event.payload.get("intent_id"),
                "symbol": event.payload.get("symbol"),
            }
        elif event.event_type in {EventType.ORDER_ACCEPTED, EventType.ORDER_PARTIALLY_FILLED}:
            open_orders[event.aggregate_id] = {
                "order_id": event.aggregate_id,
                "status": event.event_type.value.removeprefix("ORDER_"),
            }
        elif event.event_type in {EventType.ORDER_FILLED, EventType.ORDER_CANCELLED, EventType.ORDER_REJECTED}:
            open_orders.pop(event.aggregate_id, None)
        elif event.event_type is EventType.FILL_RECORDED:
            recent_fills.append(
                {
                    "fill_id": event.payload.get("fill_id"),
                    "order_id": event.payload.get("order_id"),
                    "symbol": event.payload.get("symbol"),
                    "side": event.payload.get("side"),
                    "fill_quantity": event.payload.get("fill_quantity"),
                    "fill_price": event.payload.get("fill_price"),
                }
            )
        elif event.event_type is EventType.PORTFOLIO_SNAPSHOT:
            latest_portfolio = dict(event.payload)

    current_positions: list[dict[str, object]] = []
    if portfolio_state is not None:
        latest_portfolio = latest_portfolio or {
            "cash": portfolio_state.cash,
            "gross_exposure": portfolio_state.gross_exposure,
            "equity": portfolio_state.equity,
        }
        current_positions = [
            {
                "symbol": position.symbol,
                "quantity": position.quantity,
                "average_price": position.average_price,
            }
            for position in portfolio_state.positions.values()
            if position.quantity != 0
        ]

    return LifecycleSnapshot(
        latest_signal=latest_signal,
        latest_intent=latest_intent,
        latest_risk=latest_risk,
        latest_order=latest_order,
        open_orders=list(open_orders.values()),
        recent_fills=recent_fills[-10:],
        current_positions=current_positions,
        latest_portfolio=latest_portfolio,
        timeline_rows=timeline_rows[-20:],
    )


def render_trade_lifecycle_panel(snapshot: LifecycleSnapshot) -> None:
    st.markdown("### Trade Lifecycle")
    col_signal, col_intent, col_risk = st.columns(3)
    with col_signal:
        st.markdown("**Latest Signal**")
        st.json(snapshot.latest_signal or {}, expanded=False)
    with col_intent:
        st.markdown("**Latest Intent**")
        st.json(snapshot.latest_intent or {}, expanded=False)
    with col_risk:
        st.markdown("**Risk Decision**")
        st.json(snapshot.latest_risk or {}, expanded=False)
    st.markdown("**Intent Status**")
    st.json(snapshot.latest_intent or {}, expanded=False)
    st.markdown("**Latest Order**")
    st.json(snapshot.latest_order or {}, expanded=False)

    col_open, col_filled = st.columns(2)
    with col_open:
        st.markdown("**Open Orders**")
        st.dataframe(pd.DataFrame(snapshot.open_orders), use_container_width=True, hide_index=True)
    with col_filled:
        st.markdown("**Recent Fills**")
        st.dataframe(pd.DataFrame(snapshot.recent_fills), use_container_width=True, hide_index=True)

    st.markdown("**Current Position**")
    st.dataframe(pd.DataFrame(snapshot.current_positions), use_container_width=True, hide_index=True)
    st.markdown("**Portfolio Snapshot**")
    st.json(snapshot.latest_portfolio or {}, expanded=False)
    st.markdown("**Event Timeline**")
    st.dataframe(pd.DataFrame(snapshot.timeline_rows), use_container_width=True, hide_index=True)
