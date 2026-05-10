from __future__ import annotations

from typing import Mapping

import plotly.graph_objects as go
import streamlit as st

CHART_INTERACTION_CONFIG = {
    "scrollZoom": True,
    "doubleClick": "reset+autosize",
    "displaylogo": False,
    "responsive": True,
}


def render_kpi_strip(kpis: Mapping[str, float | str]) -> None:
    cols = st.columns(max(1, len(kpis)))
    for column, (label, value) in zip(cols, kpis.items()):
        with column:
            st.metric(label, value)


def render_chart_workspace(
    *,
    price_chart: go.Figure,
    secondary_chart: go.Figure | None = None,
    title: str,
    summary: str | None = None,
) -> None:
    st.markdown(f"### {title}")
    if summary:
        st.caption(summary)
    st.plotly_chart(
        price_chart, use_container_width=True, config=CHART_INTERACTION_CONFIG
    )
    if secondary_chart is not None:
        st.plotly_chart(
            secondary_chart, use_container_width=True, config=CHART_INTERACTION_CONFIG
        )
