from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

COLOR_UP = "#10b981"
COLOR_DOWN = "#f43f5e"
COLOR_PRIMARY = "#3b82f6"
COLOR_GRID = "rgba(255, 255, 255, 0.05)"

DEFAULT_VISIBLE_BARS = 180


def _initial_x_range(
    df: pd.DataFrame, visible_bars: int | None
) -> list[pd.Timestamp] | None:
    if visible_bars is None or df.empty or len(df.index) <= visible_bars:
        return None
    return [df.index[-visible_bars], df.index[-1]]


def create_price_chart(
    df: pd.DataFrame,
    title: str = "Price Action",
    chart_type: str = "Candlestick",
    visible_bars: int | None = DEFAULT_VISIBLE_BARS,
) -> go.Figure:
    """Create the primary price chart for the trading workspace."""
    fig = go.Figure()

    if chart_type == "Line":
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["close"],
                mode="lines",
                name="Close",
                line=dict(color="white", width=2),
            )
        )
    elif chart_type == "OHLC":
        fig.add_trace(
            go.Ohlc(
                x=df.index,
                open=df["open"],
                high=df["high"],
                low=df["low"],
                close=df["close"],
                increasing_line_color=COLOR_UP,
                decreasing_line_color=COLOR_DOWN,
                name="OHLC",
                hovertemplate=(
                    "Time=%{x}<br>"
                    "Open=%{open}<br>"
                    "High=%{high}<br>"
                    "Low=%{low}<br>"
                    "Close=%{close}<extra></extra>"
                ),
            )
        )
    else:
        fig.add_trace(
            go.Candlestick(
                x=df.index,
                open=df["open"],
                high=df["high"],
                low=df["low"],
                close=df["close"],
                increasing_line_color=COLOR_UP,
                decreasing_line_color=COLOR_DOWN,
                name="Candles",
                hovertemplate=(
                    "Time=%{x}<br>"
                    "Open=%{open}<br>"
                    "High=%{high}<br>"
                    "Low=%{low}<br>"
                    "Close=%{close}<extra></extra>"
                ),
            )
        )

    if "sma_20" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["sma_20"],
                mode="lines",
                name="SMA 20",
                line=dict(color="#fbbf24", width=1.5),
            )
        )
    if "sma_50" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["sma_50"],
                mode="lines",
                name="SMA 50",
                line=dict(color="#8b5cf6", width=1.5),
            )
        )

    if "signal" in df.columns:
        buy_signals = df[df["signal"] == 1]
        sell_signals = df[df["signal"] == -1]
        fig.add_trace(
            go.Scatter(
                x=buy_signals.index,
                y=buy_signals["close"] * 0.97,
                mode="markers",
                name="Buy Signal",
                marker=dict(
                    symbol="triangle-up",
                    size=13,
                    color=COLOR_UP,
                    line=dict(width=1, color="white"),
                ),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=sell_signals.index,
                y=sell_signals["close"] * 1.03,
                mode="markers",
                name="Sell Signal",
                marker=dict(
                    symbol="triangle-down",
                    size=13,
                    color=COLOR_DOWN,
                    line=dict(width=1, color="white"),
                ),
            )
        )

    fig.update_layout(
        title=dict(text=title, font=dict(size=18, color="white")),
        xaxis_title="Time",
        yaxis_title="Price",
        template="plotly_dark",
        height=620,
        margin=dict(l=42, r=28, t=54, b=42),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        hovermode="x",
        dragmode="pan",
        uirevision="price-chart",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.01,
            xanchor="left",
            x=0,
            bgcolor="rgba(0,0,0,0)",
        ),
    )
    fig.update_xaxes(
        gridcolor=COLOR_GRID,
        showgrid=True,
        showspikes=True,
        spikemode="across",
        spikesnap="cursor",
        spikethickness=1,
        rangeslider=dict(visible=False),
        range=_initial_x_range(df, visible_bars),
    )
    fig.update_yaxes(
        gridcolor=COLOR_GRID,
        showgrid=True,
        showspikes=True,
        spikemode="across",
        spikesnap="cursor",
        spikethickness=1,
    )
    return fig


def create_equity_curve(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["equity"],
            mode="lines",
            name="Equity",
            line=dict(color=COLOR_PRIMARY, width=3),
            fill="tozeroy",
            fillcolor="rgba(59, 130, 246, 0.1)",
        )
    )
    fig.update_layout(
        title=dict(text="Equity Curve", font=dict(size=18, color="white")),
        xaxis_title="Time",
        yaxis_title="Equity",
        template="plotly_dark",
        height=400,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor=COLOR_GRID),
        yaxis=dict(gridcolor=COLOR_GRID),
    )
    return fig


def create_forecast_chart(df: pd.DataFrame, forecast_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()

    hist_subset = df.tail(30)
    fig.add_trace(
        go.Scatter(
            x=hist_subset.index,
            y=hist_subset["close"],
            mode="lines+markers",
            name="Historical Close",
            line=dict(color="white", width=2),
        )
    )

    if not forecast_df.empty:
        fig.add_trace(
            go.Scatter(
                x=forecast_df["date"],
                y=forecast_df["predicted_price"],
                mode="lines+markers",
                name="Forecast",
                line=dict(color="#fbbf24", width=2, dash="dash"),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=pd.concat([forecast_df["date"], forecast_df["date"][::-1]]),
                y=pd.concat(
                    [forecast_df["upper_bound"], forecast_df["lower_bound"][::-1]]
                ),
                fill="toself",
                fillcolor="rgba(251, 191, 36, 0.1)",
                line=dict(color="rgba(251, 191, 36, 0)"),
                hoverinfo="skip",
                showlegend=True,
                name="Forecast Band",
            )
        )

    fig.update_layout(
        title=dict(text="Scenario Forecast", font=dict(size=18, color="white")),
        xaxis_title="Time",
        yaxis_title="Price",
        template="plotly_dark",
        height=400,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor=COLOR_GRID),
        yaxis=dict(gridcolor=COLOR_GRID),
    )
    return fig


def create_rsi_chart(
    df: pd.DataFrame, overbought: int = 70, oversold: int = 30
) -> go.Figure:
    fig = go.Figure()
    if "rsi_14" not in df.columns:
        return fig

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["rsi_14"],
            mode="lines",
            name="RSI 14",
            line=dict(color="#ec4899", width=2),
        )
    )
    fig.add_hline(
        y=overbought,
        line_dash="dash",
        line_color=COLOR_DOWN,
        annotation_text="Overbought",
        annotation_font_color=COLOR_DOWN,
    )
    fig.add_hline(
        y=oversold,
        line_dash="dash",
        line_color=COLOR_UP,
        annotation_text="Oversold",
        annotation_font_color=COLOR_UP,
    )

    fig.update_layout(
        title=dict(text="RSI 14", font=dict(size=16, color="white")),
        yaxis=dict(range=[0, 100], gridcolor=COLOR_GRID),
        xaxis=dict(gridcolor=COLOR_GRID),
        template="plotly_dark",
        height=300,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig
