from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

import streamlit as st


@dataclass(frozen=True)
class WatchlistRow:
    symbol: str
    last_price: float | None = None
    change_pct: float | None = None
    volume: float | None = None


def render_watchlist(
    rows: Iterable[WatchlistRow],
    *,
    selected_symbol: str,
    on_select: Callable[[str], None] | None = None,
) -> None:
    st.markdown("#### Watchlist")
    for row in rows:
        price_text = "--" if row.last_price is None else f"{row.last_price:,.2f}"
        change_text = "--" if row.change_pct is None else f"{row.change_pct:+.2%}"
        volume_text = "--" if row.volume is None else f"{row.volume:,.0f}"
        button_type = "primary" if row.symbol == selected_symbol else "secondary"
        if st.button(
            f"{row.symbol}  {price_text}  {change_text}",
            key=f"watchlist:{row.symbol}",
            use_container_width=True,
            type=button_type,
        ):
            if on_select is not None:
                on_select(row.symbol)
        st.caption(f"Vol {volume_text}")
