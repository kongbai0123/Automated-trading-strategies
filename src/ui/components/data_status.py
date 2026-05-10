from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import streamlit as st


@dataclass(frozen=True)
class DataStatus:
    badge_label: str
    tone: str
    message: str
    details: list[str]


def build_data_status(metadata: dict[str, Any]) -> DataStatus:
    source = metadata.get("data_source", "unknown")
    fallback_used = bool(metadata.get("fallback_used", False))
    is_stale = bool(metadata.get("is_stale", False))
    warnings = list(metadata.get("data_warnings", []))
    last_bar_time = metadata.get("last_bar_time")
    details: list[str] = []
    if isinstance(last_bar_time, datetime):
        details.append(f"Last bar time: {last_bar_time:%Y-%m-%d %H:%M:%S}")

    if source == "live_yfinance":
        badge_label = "Live"
        tone = "info"
        message = "Live market data loaded successfully."
    elif source == "local_csv" and fallback_used:
        badge_label = "Local Cache"
        tone = "warning"
        message = warnings[0] if warnings else "Live data unavailable. Using local CSV fallback."
    else:
        badge_label = "Unknown Source"
        tone = "warning"
        message = "Market data source could not be classified."

    if is_stale:
        details.append("Data is marked stale for execution policy decisions.")

    return DataStatus(
        badge_label=badge_label,
        tone=tone,
        message=message,
        details=details,
    )


def render_data_status(metadata: dict[str, Any]) -> None:
    status = build_data_status(metadata)
    st.caption(f"Data Source: {status.badge_label}")
    if status.tone == "warning":
        st.warning(status.message)
    elif status.tone == "error":
        st.error(status.message)
    else:
        st.info(status.message)
    for detail in status.details:
        st.caption(detail)
