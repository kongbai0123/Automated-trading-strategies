from __future__ import annotations

from typing import Any

import pandas as pd

from src.storage import ensure_storage
from src.strategy_registry import StrategyRegistry
from src.trading.engine import TradingEngine
from src.trading.journal import InMemoryJournal
from src.trading.risk import RiskConfig
from src.ui.components.watchlist import WatchlistRow


def build_risk_config(*, semi_auto: bool) -> RiskConfig:
    return RiskConfig(
        max_position_size=100,
        max_symbol_exposure=250_000.0,
        max_total_exposure=500_000.0,
        max_daily_loss=100_000.0,
        semi_auto=semi_auto,
        cooldown_minutes=30,
        symbol_allowlist=None,
    )


def init_workspace_state(
    session_state: Any,
    *,
    default_symbol: str,
    execution_modes: list[str],
) -> None:
    ensure_storage()
    defaults = {
        "selected_symbol": default_symbol,
        "selected_timeframe": "1d",
        "selected_period": "2y",
        "selected_strategy": StrategyRegistry.get_available_strategies()[0],
        "selected_execution_mode": execution_modes[0],
        "analysis_result": None,
        "analysis_error": None,
    }
    for key, value in defaults.items():
        session_state.setdefault(key, value)

    session_state.setdefault("paper_journal", InMemoryJournal())
    session_state.setdefault(
        "paper_engine",
        TradingEngine.for_paper_trading(
            risk_config=build_risk_config(semi_auto=False),
            journal=session_state["paper_journal"],
            starting_cash=1_000_000.0,
        ),
    )
    session_state.setdefault("semi_journal", InMemoryJournal())
    session_state.setdefault(
        "semi_engine",
        TradingEngine.for_semi_auto(
            risk_config=build_risk_config(semi_auto=True),
            journal=session_state["semi_journal"],
            starting_cash=1_000_000.0,
        ),
    )


def current_engine(session_state: Any, mode: str) -> TradingEngine:
    return (
        session_state["paper_engine"] if mode == "Paper Trading" else session_state["semi_engine"]
    )


def current_journal(session_state: Any, mode: str) -> InMemoryJournal:
    return (
        session_state["paper_journal"] if mode == "Paper Trading" else session_state["semi_journal"]
    )


def build_watchlist_rows(
    *,
    watchlist_symbols: list[str],
    current_symbol: str,
    dataframe: pd.DataFrame | None,
) -> list[WatchlistRow]:
    effective_symbols = list(watchlist_symbols)
    if current_symbol not in effective_symbols:
        effective_symbols = [current_symbol] + effective_symbols

    last_price = None
    change_pct = None
    volume = None
    if dataframe is not None and not dataframe.empty:
        last_price = float(dataframe["close"].iloc[-1])
        if len(dataframe) > 1 and float(dataframe["close"].iloc[-2]) != 0:
            previous_close = float(dataframe["close"].iloc[-2])
            change_pct = (float(dataframe["close"].iloc[-1]) - previous_close) / previous_close
        volume = float(dataframe["volume"].iloc[-1]) if "volume" in dataframe.columns else None

    rows: list[WatchlistRow] = []
    for symbol in effective_symbols:
        if symbol == current_symbol:
            rows.append(
                WatchlistRow(
                    symbol=symbol,
                    last_price=last_price,
                    change_pct=change_pct,
                    volume=volume,
                )
            )
        else:
            rows.append(WatchlistRow(symbol=symbol))
    return rows
