from __future__ import annotations

from dataclasses import dataclass

import plotly.graph_objects as go

from src.ui.components.research_workspace import render_research_workspace


@dataclass(frozen=True)
class ResearchPageView:
    projection_summary: dict[str, object] | None
    forecast_chart: go.Figure | None
    notes: list[str]


def render_research_page(view: ResearchPageView) -> None:
    render_research_workspace(
        projection_summary=view.projection_summary,
        forecast_chart=view.forecast_chart,
        notes=view.notes,
    )
