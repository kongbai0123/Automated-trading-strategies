from __future__ import annotations

from collections.abc import Iterable

import plotly.graph_objects as go
import streamlit as st


def render_research_workspace(
    *,
    projection_summary: dict[str, object] | None,
    forecast_chart: go.Figure | None,
    notes: Iterable[str] | None = None,
) -> None:
    st.markdown("### Research Workspace")
    if projection_summary:
        st.json(projection_summary, expanded=False)
    else:
        st.info("No research projection available.")
    if forecast_chart is not None:
        st.plotly_chart(forecast_chart, use_container_width=True)
    if notes:
        st.markdown("#### Notes")
        for note in notes:
            st.write(f"- {note}")
