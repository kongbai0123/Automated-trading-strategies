from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

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


STATUS_COLORS = {
    "APPROVED": "#22c55e",
    "APPROVED_FOR_EXECUTION": "#22c55e",
    "ACCEPTED": "#22c55e",
    "FILLED": "#22c55e",
    "RISK_APPROVED": "#22c55e",
    "PENDING_APPROVAL": "#f59e0b",
    "PENDING_RISK_CHECK": "#f59e0b",
    "PARTIALLY_FILLED": "#f59e0b",
    "SUBMITTED": "#38bdf8",
    "REJECTED": "#ef4444",
    "RISK_REJECTED": "#ef4444",
    "CANCELLED": "#94a3b8",
    "EMITTED": "#38bdf8",
}


def _status_color(status: object | None) -> str:
    return STATUS_COLORS.get(str(status or "").upper(), "#64748b")


def _status_pill(label: str, status: object | None) -> str:
    status_text = str(status or "N/A")
    return (
        "<div style='display:flex;justify-content:space-between;align-items:center;"
        "gap:0.5rem;padding:0.35rem 0;border-bottom:1px solid rgba(148,163,184,0.12);'>"
        f"<span style='color:#94a3b8;font-size:0.78rem;'>{label}</span>"
        f"<span style='background:{_status_color(status)};color:#020617;border-radius:999px;"
        "padding:0.12rem 0.5rem;font-size:0.72rem;font-weight:700;'>"
        f"{status_text}</span></div>"
    )


def _compact_kv(label: str, value: object | None) -> str:
    value_text = "N/A" if value is None else str(value)
    return (
        "<div style='display:flex;justify-content:space-between;gap:0.75rem;"
        "padding:0.18rem 0;font-size:0.78rem;'>"
        f"<span style='color:#94a3b8;'>{label}</span>"
        f"<span style='color:#e2e8f0;font-weight:600;text-align:right;'>{value_text}</span>"
        "</div>"
    )


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
        elif event.event_type in {
            EventType.ORDER_SUBMITTED,
            EventType.ORDER_ACCEPTED,
            EventType.ORDER_PARTIALLY_FILLED,
            EventType.ORDER_FILLED,
            EventType.ORDER_CANCELLED,
            EventType.ORDER_REJECTED,
        }:
            latest_order = {
                "order_id": event.aggregate_id,
                "status": event.event_type.value.removeprefix("ORDER_"),
                "intent_id": event.payload.get("intent_id"),
                "symbol": event.payload.get("symbol"),
            }
            if event.event_type in {
                EventType.ORDER_ACCEPTED,
                EventType.ORDER_PARTIALLY_FILLED,
            }:
                open_orders[event.aggregate_id] = {
                    "order_id": event.aggregate_id,
                    "status": event.event_type.value.removeprefix("ORDER_"),
                    "intent_id": event.payload.get("intent_id"),
                }
            elif event.event_type in {
                EventType.ORDER_FILLED,
                EventType.ORDER_CANCELLED,
                EventType.ORDER_REJECTED,
            }:
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
    signal = snapshot.latest_signal or {}
    intent = snapshot.latest_intent or {}
    risk = snapshot.latest_risk or {}
    order = snapshot.latest_order or {}
    portfolio = snapshot.latest_portfolio or {}

    st.markdown(
        "".join(
            [
                _status_pill("Signal", "EMITTED" if snapshot.latest_signal else None),
                _status_pill("Intent", intent.get("status")),
                _status_pill("Risk", risk.get("status")),
                _status_pill("Order", order.get("status")),
            ]
        ),
        unsafe_allow_html=True,
    )

    st.markdown("**Latest Signal**")
    st.markdown(
        "".join(
            [
                _compact_kv("Symbol", signal.get("symbol")),
                _compact_kv("Signal ID", signal.get("signal_id")),
                _compact_kv("Market Time", signal.get("market_time")),
            ]
        ),
        unsafe_allow_html=True,
    )

    st.markdown("**Risk Decision**")
    st.markdown(
        "".join(
            [
                _compact_kv("Status", risk.get("status")),
                _compact_kv("Reject Reasons", ", ".join(risk.get("reject_reasons", []))),
                _compact_kv("Warnings", ", ".join(risk.get("warning_reasons", []))),
            ]
        ),
        unsafe_allow_html=True,
    )

    col_open, col_filled = st.columns(2)
    with col_open:
        st.markdown("**Open Orders**")
        st.dataframe(
            pd.DataFrame(snapshot.open_orders),
            use_container_width=True,
            hide_index=True,
        )
    with col_filled:
        st.markdown("**Recent Fills**")
        st.dataframe(
            pd.DataFrame(snapshot.recent_fills),
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("**Current Position**")
    st.dataframe(
        pd.DataFrame(snapshot.current_positions),
        use_container_width=True,
        hide_index=True,
    )
    st.markdown("**Portfolio Snapshot**")
    st.markdown(
        "".join(
            [
                _compact_kv("Cash", portfolio.get("cash")),
                _compact_kv("Equity", portfolio.get("equity")),
                _compact_kv("Exposure", portfolio.get("gross_exposure")),
            ]
        ),
        unsafe_allow_html=True,
    )
    st.markdown("**Event Timeline**")
    st.dataframe(pd.DataFrame(snapshot.timeline_rows), use_container_width=True, hide_index=True)
