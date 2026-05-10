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
    open_orders: list[dict[str, object]]
    filled_orders: list[dict[str, object]]
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
    latest_portfolio = None
    timeline_rows: list[dict[str, object]] = []
    open_orders: dict[str, dict[str, object]] = {}
    filled_orders: list[dict[str, object]] = []

    for event in events:
        timeline_rows.append(
            {
                "time": event.market_time,
                "event_type": event.event_type.value,
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
            }
        elif event.event_type in {EventType.RISK_APPROVED, EventType.RISK_REJECTED}:
            latest_risk = {
                "status": event.payload.get("decision_status"),
                "reject_reasons": event.payload.get("reject_reasons", []),
                "warning_reasons": event.payload.get("warning_reasons", []),
            }
        elif event.event_type in {EventType.ORDER_ACCEPTED, EventType.ORDER_PARTIALLY_FILLED}:
            open_orders[event.aggregate_id] = {
                "order_id": event.aggregate_id,
                "status": event.event_type.value,
            }
        elif event.event_type in {EventType.ORDER_FILLED, EventType.ORDER_CANCELLED, EventType.ORDER_REJECTED}:
            open_orders.pop(event.aggregate_id, None)
            filled_orders.append(
                {
                    "order_id": event.aggregate_id,
                    "status": event.event_type.value,
                    "symbol": event.payload.get("symbol"),
                    "fill_quantity": event.payload.get("fill_quantity"),
                    "fill_price": event.payload.get("fill_price"),
                }
            )
        elif event.event_type is EventType.PORTFOLIO_SNAPSHOT:
            latest_portfolio = dict(event.payload)

    if portfolio_state is not None:
        latest_portfolio = latest_portfolio or {
            "cash": portfolio_state.cash,
            "gross_exposure": portfolio_state.gross_exposure,
            "equity": portfolio_state.equity,
        }

    return LifecycleSnapshot(
        latest_signal=latest_signal,
        latest_intent=latest_intent,
        latest_risk=latest_risk,
        open_orders=list(open_orders.values()),
        filled_orders=filled_orders[-10:],
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

    col_open, col_filled = st.columns(2)
    with col_open:
        st.markdown("**Open Orders**")
        st.dataframe(pd.DataFrame(snapshot.open_orders), use_container_width=True, hide_index=True)
    with col_filled:
        st.markdown("**Filled Orders**")
        st.dataframe(pd.DataFrame(snapshot.filled_orders), use_container_width=True, hide_index=True)

    st.markdown("**Portfolio Snapshot**")
    st.json(snapshot.latest_portfolio or {}, expanded=False)
    st.markdown("**Journal Timeline**")
    st.dataframe(pd.DataFrame(snapshot.timeline_rows), use_container_width=True, hide_index=True)

