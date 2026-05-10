from __future__ import annotations

from datetime import datetime
from typing import Any

import streamlit as st

from src.app_services.analysis_service import (
    build_kpis,
    build_scanner_rows,
    load_analysis,
)
from src.app_services.error_presenter import build_controlled_error_payload
from src.app_services.execution_service import execute_latest_signal
from src.app_services.market_status_service import build_market_status_items
from src.app_services.timeframe_options import (
    normalize_period_for_timeframe,
    period_options_for_timeframe,
)
from src.app_services.workspace_state import (
    build_watchlist_rows,
    current_engine,
    current_journal,
    init_workspace_state,
)
from src.charting import (
    create_equity_curve,
    create_forecast_chart,
    create_price_chart,
    create_rsi_chart,
)
from src.market_data import ControlledMarketDataError
from src.predictor import get_ai_projection, predict_future_prices
from src.storage import get_watchlist, remove_from_watchlist, save_to_watchlist
from src.strategy_registry import StrategyRegistry
from src.ui.components.data_status import render_data_status
from src.ui.components.market_bar import MarketStatusItem, render_market_bar
from src.ui.components.watchlist import render_watchlist
from src.ui.components.workspace_toolbar import render_workspace_toolbar
from src.ui.pages.backtest_workspace import (
    BacktestWorkspaceView,
    render_backtest_workspace,
)
from src.ui.pages.research_page import ResearchPageView, render_research_page
from src.ui.pages.scanner_page import ScannerPageView, render_scanner_page
from src.ui.pages.trading_workspace import (
    TradingWorkspaceView,
    render_trading_workspace,
)
from src.ui_pipeline import load_config

st.set_page_config(
    page_title="Professional Quant Trading Workspace",
    layout="wide",
    initial_sidebar_state="collapsed",
)

TIMEFRAME_LABELS = {
    "1m": "1 Minute",
    "5m": "5 Minutes",
    "15m": "15 Minutes",
    "30m": "30 Minutes",
    "60m": "1 Hour",
    "1d": "1 Day",
    "1wk": "1 Week",
    "1mo": "1 Month",
}
TIMEFRAME_OPTIONS = list(TIMEFRAME_LABELS.keys())
EXECUTION_MODES = ["Paper Trading", "Semi Auto"]
MARKET_TICKERS = {
    "TAIEX": "^TWII",
    "NASDAQ": "^IXIC",
    "BTC": "BTC-USD",
    "VIX": "^VIX",
}
DEFAULT_SYMBOL = "2330.TW"
DEFAULT_REQUESTED_QUANTITY = 10
CONFIG = load_config()
DEFAULT_TRANSACTION_COST = float(CONFIG.get("transaction_cost", 0.001))


def inject_css() -> None:
    st.markdown(
        """
        <style>
        .stApp { background: #0b1220; color: #e2e8f0; }
        .block-container { padding-top: 0.6rem; padding-bottom: 1rem; max-width: 100%; }
        .qp-market-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.45rem 0.8rem;
            border: 1px solid rgba(148, 163, 184, 0.15);
            background: rgba(15, 23, 42, 0.85);
            margin-bottom: 0.8rem;
            font-size: 0.82rem;
        }
        .qp-market-group { display: flex; gap: 1rem; flex-wrap: wrap; }
        .qp-market-item { display: flex; gap: 0.45rem; align-items: center; }
        .qp-market-label { color: #94a3b8; }
        .qp-market-value { font-weight: 600; }
        .qp-market-change { font-weight: 600; }
        .qp-market-meta { color: #94a3b8; }
        div[data-testid="stMetric"] {
            background: rgba(15, 23, 42, 0.7);
            border: 1px solid rgba(148, 163, 184, 0.15);
            border-radius: 8px;
            padding: 0.35rem 0.65rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(ttl=180, show_spinner=False)
def load_market_snapshot() -> list[MarketStatusItem]:
    return build_market_status_items(MARKET_TICKERS)


def render_workspace(result: dict[str, Any]) -> None:
    dataframe = result["df"]
    render_data_status(result["metadata"])
    selected_symbol = st.session_state["selected_symbol"]
    execution_mode = st.session_state["selected_execution_mode"]
    journal = current_journal(st.session_state, execution_mode)
    engine = current_engine(st.session_state, execution_mode)
    try:
        portfolio_state = engine.replay_portfolio(journal.read_all())
    except ValueError:
        portfolio_state = None

    price_chart = create_price_chart(dataframe, title=f"{selected_symbol} Price Action")
    rsi_chart = create_rsi_chart(dataframe)
    equity_chart = create_equity_curve(dataframe)
    projection = get_ai_projection(dataframe)
    forecast_chart = create_forecast_chart(dataframe, predict_future_prices(dataframe))
    strategy_name = result["metadata"]["strategy_name"]
    latest_signal = int(dataframe["signal"].iloc[-1]) if "signal" in dataframe.columns else 0
    latest_close = float(dataframe["close"].iloc[-1])

    render_trading_workspace(
        TradingWorkspaceView(
            title=f"{selected_symbol} | {strategy_name}",
            price_chart=price_chart,
            secondary_chart=rsi_chart,
            kpis=build_kpis(result),
            journal_events=journal.read_all(),
            portfolio_state=portfolio_state,
            summary=f"Latest close {latest_close:,.2f} | Latest signal {latest_signal} | Mode {execution_mode}",
        )
    )

    backtest_tab, scanner_tab, research_tab = st.tabs(["Backtest", "Scanner", "Research"])
    with backtest_tab:
        render_backtest_workspace(
            BacktestWorkspaceView(
                kpis=build_kpis(result),
                equity_chart=equity_chart,
                dataframe=dataframe,
            )
        )
    with scanner_tab:
        scanner_rows = build_scanner_rows(
            result,
            symbol=st.session_state["selected_symbol"],
            strategy_name=st.session_state["selected_strategy"],
        )
        render_scanner_page(
            ScannerPageView(
                rows=scanner_rows,
                narrative=[
                    "Scanner stays secondary to the chart and lifecycle panel.",
                    "Current candidate score is derived from price structure, momentum, volume, and risk.",
                ],
            )
        )
    with research_tab:
        render_research_page(
            ResearchPageView(
                projection_summary=projection,
                forecast_chart=forecast_chart,
                notes=[
                    "Research outputs remain tertiary and do not displace price action.",
                    "Forecasts are scenario-based and should not override risk constraints.",
                ],
            )
        )


def main() -> None:
    inject_css()
    init_workspace_state(
        st.session_state,
        default_symbol=DEFAULT_SYMBOL,
        execution_modes=EXECUTION_MODES,
    )
    render_market_bar(
        load_market_snapshot(),
        market_label="Global Market Tape",
        as_of=datetime.now(),
        market_status="Live",
    )

    analysis_result = st.session_state.get("analysis_result")
    current_dataframe = analysis_result["df"] if analysis_result else None

    left_col, right_col = st.columns([1.0, 4.2])
    with left_col:
        watchlist_rows = build_watchlist_rows(
            watchlist_symbols=get_watchlist(),
            current_symbol=st.session_state["selected_symbol"],
            dataframe=current_dataframe,
        )
        render_watchlist(
            watchlist_rows,
            selected_symbol=st.session_state["selected_symbol"],
            on_select=lambda symbol: st.session_state.__setitem__("selected_symbol", symbol),
        )
        new_symbol = st.text_input("Add Symbol", value="", placeholder="e.g. NVDA")
        add_col, remove_col = st.columns(2)
        with add_col:
            if st.button("Add", use_container_width=True) and new_symbol:
                save_to_watchlist(new_symbol.upper())
        with remove_col:
            if st.button("Remove", use_container_width=True):
                remove_from_watchlist(st.session_state["selected_symbol"])

    with right_col:
        period_options = period_options_for_timeframe(st.session_state["selected_timeframe"])
        st.session_state["selected_period"] = normalize_period_for_timeframe(
            st.session_state["selected_period"],
            st.session_state["selected_timeframe"],
        )
        toolbar_state = render_workspace_toolbar(
            symbols=[
                st.session_state["selected_symbol"],
                *[
                    symbol
                    for symbol in get_watchlist()
                    if symbol != st.session_state["selected_symbol"]
                ],
            ],
            selected_symbol=st.session_state["selected_symbol"],
            timeframes=TIMEFRAME_OPTIONS,
            selected_timeframe=st.session_state["selected_timeframe"],
            periods=period_options,
            selected_period=st.session_state["selected_period"],
            strategies=StrategyRegistry.get_available_strategies(),
            selected_strategy=st.session_state["selected_strategy"],
            execution_modes=EXECUTION_MODES,
            selected_execution_mode=st.session_state["selected_execution_mode"],
        )
        st.session_state["selected_symbol"] = toolbar_state.symbol
        st.session_state["selected_timeframe"] = toolbar_state.timeframe
        st.session_state["selected_period"] = toolbar_state.period
        st.session_state["selected_strategy"] = toolbar_state.strategy_name
        st.session_state["selected_execution_mode"] = toolbar_state.execution_mode

        run_col, paper_col, semi_col = st.columns([1.1, 1.2, 1.2])
        with run_col:
            if st.button("Run Analysis", use_container_width=True, type="primary"):
                try:
                    st.session_state["analysis_result"] = load_analysis(
                        symbol=toolbar_state.symbol,
                        strategy_name=toolbar_state.strategy_name,
                        period=toolbar_state.period,
                        interval=toolbar_state.timeframe,
                        transaction_cost=DEFAULT_TRANSACTION_COST,
                    )
                    st.session_state["analysis_error"] = None
                except ControlledMarketDataError as exc:
                    st.session_state["analysis_result"] = None
                    st.session_state["analysis_error"] = build_controlled_error_payload(
                        symbol=exc.symbol,
                        attempted_source=exc.attempted_source,
                        fallback_attempted=exc.fallback_attempted,
                        diagnostics=exc.diagnostics,
                        message=str(exc),
                    )
        with paper_col:
            if st.button("Trigger Paper Flow", use_container_width=True):
                tone, message = execute_latest_signal(
                    engine=current_engine(st.session_state, "Paper Trading"),
                    result=st.session_state.get("analysis_result"),
                    symbol=st.session_state["selected_symbol"],
                    strategy_name=st.session_state["selected_strategy"],
                    timeframe=st.session_state["selected_timeframe"],
                    requested_quantity=DEFAULT_REQUESTED_QUANTITY,
                )
                getattr(st, tone)(f"Paper Trading: {message}")
        with semi_col:
            if st.button("Trigger Semi Auto", use_container_width=True):
                tone, message = execute_latest_signal(
                    engine=current_engine(st.session_state, "Semi Auto"),
                    result=st.session_state.get("analysis_result"),
                    symbol=st.session_state["selected_symbol"],
                    strategy_name=st.session_state["selected_strategy"],
                    timeframe=st.session_state["selected_timeframe"],
                    requested_quantity=DEFAULT_REQUESTED_QUANTITY,
                )
                getattr(st, tone)(f"Semi Auto: {message}")

        if st.session_state.get("analysis_error") is not None:
            error = st.session_state["analysis_error"]
            st.error(error["message"])
            st.caption(f"Symbol: {error['symbol']}")
            st.caption(f"Attempted source: {error['attempted_source']}")
            st.caption(f"Fallback attempted: {error['fallback_attempted']}")
            if error["diagnostics"]:
                st.json(error["diagnostics"], expanded=False)
            st.info("Next action: verify network access or refresh local CSV data under data/.")
            return

        if st.session_state.get("analysis_result") is None:
            st.info("Run analysis to load the trading workspace.")
            return

        render_workspace(st.session_state["analysis_result"])


if __name__ == "__main__":
    main()
