from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.ui.components.chart_workspace import render_kpi_strip


@dataclass(frozen=True)
class BacktestWorkspaceView:
    kpis: Mapping[str, float | str]
    equity_chart: go.Figure | None
    dataframe: pd.DataFrame


def render_backtest_workspace(view: BacktestWorkspaceView) -> None:
    st.markdown("### Backtest Workspace")
    render_kpi_strip(view.kpis)
    if view.equity_chart is not None:
        st.plotly_chart(view.equity_chart, use_container_width=True)
    st.dataframe(view.dataframe.tail(50), use_container_width=True)
