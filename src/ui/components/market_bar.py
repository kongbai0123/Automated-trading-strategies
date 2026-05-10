from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

import streamlit as st


@dataclass(frozen=True)
class MarketStatusItem:
    label: str
    value: str
    change_pct: float


def render_market_bar(
    items: Iterable[MarketStatusItem],
    *,
    market_label: str,
    as_of: datetime,
    market_status: str,
) -> None:
    item_markup: list[str] = []
    for item in items:
        color = "#22c55e" if item.change_pct >= 0 else "#ef4444"
        item_markup.append(
            (
                "<div class='qp-market-item'>"
                f"<span class='qp-market-label'>{item.label}</span>"
                f"<span class='qp-market-value' style='color:{color}'>{item.value}</span>"
                f"<span class='qp-market-change' style='color:{color}'>{item.change_pct:+.2%}</span>"
                "</div>"
            )
        )

    st.markdown(
        (
            "<div class='qp-market-bar'>"
            f"<div class='qp-market-group'>{''.join(item_markup)}</div>"
            f"<div class='qp-market-meta'>{market_label} | {market_status} | {as_of.strftime('%Y-%m-%d %H:%M:%S')}</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

