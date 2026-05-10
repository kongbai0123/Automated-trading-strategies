from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd
import streamlit as st
import yfinance as yf

from src.charting import create_equity_curve, create_forecast_chart, create_price_chart, create_rsi_chart
from src.market_data import ControlledMarketDataError
from src.predictor import get_ai_projection, predict_future_prices
from src.scanner import analyze_symbol_detailed
from src.storage import ensure_storage, get_watchlist, remove_from_watchlist, save_to_watchlist
from src.strategy_registry import StrategyRegistry
from src.trading.engine import TradingEngine
from src.trading.journal import InMemoryJournal
from src.trading.models import OrderSide, SignalEvent, generate_trace_id
from src.trading.risk import RiskConfig
from src.ui.components.data_status import render_data_status
from src.ui.components.market_bar import MarketStatusItem, render_market_bar
from src.ui.components.watchlist import WatchlistRow, render_watchlist
from src.ui.components.workspace_toolbar import render_workspace_toolbar
from src.ui.pages.backtest_workspace import BacktestWorkspaceView, render_backtest_workspace
from src.ui.pages.research_page import ResearchPageView, render_research_page
from src.ui.pages.scanner_page import ScannerPageView, render_scanner_page
from src.ui.pages.trading_workspace import TradingWorkspaceView, render_trading_workspace
from src.ui_pipeline import load_config, run_backtest_pipeline

st.set_page_config(page_title="Professional Quant Trading Workspace", layout="wide", initial_sidebar_state="collapsed")

TIMEFRAME_LABELS = {
    "1m": "1 Minute",
    "5m": "5 Minutes",
    "15m": "15 Minutes",
    "60m": "1 Hour",
    "1d": "1 Day",
    "1wk": "1 Week",
    "1mo": "1 Month",
}
TIMEFRAME_OPTIONS = list(TIMEFRAME_LABELS.keys())
PERIOD_OPTIONS = ["1mo", "3mo", "6mo", "1y", "2y", "5y"]
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


def init_session_state() -> None:
    ensure_storage()
    defaults = {
        "selected_symbol": DEFAULT_SYMBOL,
        "selected_timeframe": "1d",
        "selected_period": "2y",
        "selected_strategy": StrategyRegistry.get_available_strategies()[0],
        "selected_execution_mode": EXECUTION_MODES[0],
        "analysis_result": None,
        "analysis_error": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)

    st.session_state.setdefault("paper_journal", InMemoryJournal())
    st.session_state.setdefault(
        "paper_engine",
        TradingEngine.for_paper_trading(
            risk_config=_risk_config(semi_auto=False),
            journal=st.session_state["paper_journal"],
            starting_cash=1_000_000.0,
        ),
    )
    st.session_state.setdefault("semi_journal", InMemoryJournal())
    st.session_state.setdefault(
        "semi_engine",
        TradingEngine.for_semi_auto(
            risk_config=_risk_config(semi_auto=True),
            journal=st.session_state["semi_journal"],
            starting_cash=1_000_000.0,
        ),
    )


def _risk_config(*, semi_auto: bool) -> RiskConfig:
    return RiskConfig(
        max_position_size=100,
        max_symbol_exposure=250_000.0,
        max_total_exposure=500_000.0,
        max_daily_loss=100_000.0,
        semi_auto=semi_auto,
        cooldown_minutes=30,
        symbol_allowlist=None,
    )


@st.cache_data(ttl=180, show_spinner=False)
def load_market_snapshot() -> list[MarketStatusItem]:
    try:
        downloaded = yf.download(list(MARKET_TICKERS.values()), period="5d", progress=False, auto_adjust=False)
        close_frame = downloaded["Close"] if "Close" in downloaded else downloaded
        items: list[MarketStatusItem] = []
        for label, ticker in MARKET_TICKERS.items():
            series = close_frame[ticker].dropna()
            if len(series) >= 2:
                current = float(series.iloc[-1])
                previous = float(series.iloc[-2])
                change_pct = 0.0 if previous == 0 else (current - previous) / previous
            elif len(series) == 1:
                current = float(series.iloc[-1])
                change_pct = 0.0
            else:
                current = 0.0
                change_pct = 0.0
            items.append(MarketStatusItem(label=label, value=f"{current:,.2f}", change_pct=change_pct))
        return items
    except Exception:
        return [MarketStatusItem(label=label, value="--", change_pct=0.0) for label in MARKET_TICKERS]


def load_analysis(symbol: str, strategy_name: str, period: str, interval: str) -> dict[str, Any]:
    return run_backtest_pipeline(
        symbol=symbol,
        strategy_name=strategy_name,
        strategy_params={},
        transaction_cost=DEFAULT_TRANSACTION_COST,
        period=period,
        interval=interval,
    )


def build_signal_from_analysis(result: dict[str, Any], *, symbol: str, strategy_name: str, timeframe: str) -> SignalEvent | None:
    dataframe = result["df"]
    if "signal" not in dataframe.columns:
        return None

    actionable = dataframe[dataframe["signal"].isin([1, -1])]
    if actionable.empty:
        return None

    latest = actionable.iloc[-1]
    market_time = pd.Timestamp(latest.name).to_pydatetime()
    side = OrderSide.BUY if int(latest["signal"]) > 0 else OrderSide.SELL
    reference_price = float(latest.get("close", 0.0))
    created_at = datetime.now()
    return SignalEvent(
        signal_id=generate_trace_id("signal", strategy_name, symbol, market_time.isoformat()),
        run_id=generate_trace_id("run", symbol, timeframe, created_at.strftime("%Y%m%d")),
        strategy_id=strategy_name,
        symbol=symbol,
        timeframe=timeframe,
        side=side,
        signal_type="ENTRY",
        strength=abs(float(latest["signal"])),
        confidence=0.75,
        market_time=market_time,
        created_at=created_at,
        processed_at=created_at,
        metadata={"reference_price": reference_price},
    )


def _current_engine(mode: str) -> TradingEngine:
    return st.session_state["paper_engine"] if mode == "Paper Trading" else st.session_state["semi_engine"]


def _current_journal(mode: str) -> InMemoryJournal:
    return st.session_state["paper_journal"] if mode == "Paper Trading" else st.session_state["semi_journal"]


def execute_latest_signal(mode: str) -> None:
    result = st.session_state.get("analysis_result")
    if not result:
        st.warning("Run analysis first.")
        return

    signal = build_signal_from_analysis(
        result,
        symbol=st.session_state["selected_symbol"],
        strategy_name=st.session_state["selected_strategy"],
        timeframe=st.session_state["selected_timeframe"],
    )
    if signal is None:
        st.warning("No actionable signal found in the current dataset.")
        return

    execution_price = float(signal.metadata.get("reference_price", 0.0))
    engine = _current_engine(mode)
    outcome = engine.process_signal(
        signal,
        requested_quantity=DEFAULT_REQUESTED_QUANTITY,
        execution_price=execution_price,
    )
    if outcome.order is None:
        st.info(f"{mode}: intent stopped at {outcome.intent.status.value}.")
    else:
        st.success(f"{mode}: order {outcome.order.order_id} is {outcome.order.status.value}.")


def build_watchlist_rows(current_symbol: str, dataframe: pd.DataFrame | None) -> list[WatchlistRow]:
    watchlist_symbols = get_watchlist()
    if current_symbol not in watchlist_symbols:
        watchlist_symbols = [current_symbol] + watchlist_symbols

    last_price = None
    change_pct = None
    volume = None
    if dataframe is not None and not dataframe.empty:
        last_price = float(dataframe["close"].iloc[-1])
        if len(dataframe) > 1 and float(dataframe["close"].iloc[-2]) != 0:
            change_pct = (float(dataframe["close"].iloc[-1]) - float(dataframe["close"].iloc[-2])) / float(dataframe["close"].iloc[-2])
        volume = float(dataframe["volume"].iloc[-1]) if "volume" in dataframe.columns else None

    rows: list[WatchlistRow] = []
    for symbol in watchlist_symbols:
        if symbol == current_symbol:
            rows.append(WatchlistRow(symbol=symbol, last_price=last_price, change_pct=change_pct, volume=volume))
        else:
            rows.append(WatchlistRow(symbol=symbol))
    return rows


def build_kpis(result: dict[str, Any]) -> dict[str, str]:
    kpi = result["kpi"]
    return {
        "Return": f"{float(kpi.get('return', 0.0)):.2%}",
        "Win Rate": f"{float(kpi.get('win_rate', 0.0)):.2%}",
        "Max Drawdown": f"{float(kpi.get('max_drawdown', 0.0)):.2%}",
        "Signal": str(int(result["df"]["signal"].iloc[-1])) if "signal" in result["df"].columns else "0",
    }


def build_scanner_rows(result: dict[str, Any]) -> list[dict[str, object]]:
    analysis = analyze_symbol_detailed(result["df"], symbol=st.session_state["selected_symbol"])
    latest_close = float(result["df"]["close"].iloc[-1])
    return [
        {
            "symbol": st.session_state["selected_symbol"],
            "strategy": st.session_state["selected_strategy"],
            "score": analysis.get("score", 0),
            "trend": analysis.get("trend", "Unknown"),
            "risk": analysis.get("risk", "Unknown"),
            "last_price": latest_close,
            "reason": analysis.get("reason", ""),
        }
    ]


def render_workspace(result: dict[str, Any]) -> None:
    dataframe = result["df"]
    render_data_status(result["metadata"])
    selected_symbol = st.session_state["selected_symbol"]
    execution_mode = st.session_state["selected_execution_mode"]
    journal = _current_journal(execution_mode)
    engine = _current_engine(execution_mode)
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
        scanner_rows = build_scanner_rows(result)
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
    init_session_state()
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
        watchlist_rows = build_watchlist_rows(st.session_state["selected_symbol"], current_dataframe)
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
        toolbar_state = render_workspace_toolbar(
            symbols=[st.session_state["selected_symbol"], *[symbol for symbol in get_watchlist() if symbol != st.session_state["selected_symbol"]]],
            selected_symbol=st.session_state["selected_symbol"],
            timeframes=TIMEFRAME_OPTIONS,
            selected_timeframe=st.session_state["selected_timeframe"],
            periods=PERIOD_OPTIONS,
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
                    )
                    st.session_state["analysis_error"] = None
                except ControlledMarketDataError as exc:
                    st.session_state["analysis_result"] = None
                    st.session_state["analysis_error"] = {
                        "symbol": exc.symbol,
                        "attempted_source": exc.attempted_source,
                        "fallback_attempted": exc.fallback_attempted,
                        "diagnostics": exc.diagnostics,
                        "message": str(exc),
                    }
        with paper_col:
            if st.button("Trigger Paper Flow", use_container_width=True):
                execute_latest_signal("Paper Trading")
        with semi_col:
            if st.button("Trigger Semi Auto", use_container_width=True):
                execute_latest_signal("Semi Auto")

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
