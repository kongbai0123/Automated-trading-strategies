from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import plotly.graph_objects as go
import streamlit as st

from src.trading.models import PortfolioState
from src.ui.components.chart_workspace import render_chart_workspace, render_kpi_strip
from src.ui.components.trade_lifecycle_panel import (
    build_lifecycle_snapshot,
    render_trade_lifecycle_panel,
)


@dataclass(frozen=True)
class TradingWorkspaceView:
    title: str
    price_chart: go.Figure
    secondary_chart: go.Figure | None
    kpis: Mapping[str, float | str]
    journal_events: list
    portfolio_state: PortfolioState | None
    summary: str | None = None


def render_trading_workspace(view: TradingWorkspaceView) -> None:
    render_kpi_strip(view.kpis)
    chart_col, lifecycle_col = st.columns([3.3, 1.7])
    with chart_col:
        render_chart_workspace(
            price_chart=view.price_chart,
            secondary_chart=view.secondary_chart,
            title=view.title,
            summary=view.summary,
        )
    with lifecycle_col:
        snapshot = build_lifecycle_snapshot(
            view.journal_events, portfolio_state=view.portfolio_state
        )
        render_trade_lifecycle_panel(snapshot)
