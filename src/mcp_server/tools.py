from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict
from typing import Any

from src.app_services.analysis_service import load_analysis
from src.app_services.execution_service import (
    build_signal_from_analysis,
    build_trade_lifecycle_view_model,
)
from src.app_services.workspace_state import build_risk_config
from src.market_data import ControlledMarketDataError, fetch_market_data
from src.strategy_registry import StrategyRegistry
from src.trading.engine import TradingEngine
from src.trading.journal import InMemoryJournal

from .schemas import dataframe_tail_records, ensure_json_safe

AnalysisLoader = Callable[..., dict[str, Any]]


class MCPToolError(ValueError):
    pass


class MCPToolService:
    def __init__(
        self,
        *,
        analysis_loader: AnalysisLoader = load_analysis,
        market_data_fetcher: Callable[..., Any] = fetch_market_data,
        transaction_cost: float = 0.001,
        starting_cash: float = 1_000_000.0,
    ) -> None:
        self._analysis_loader = analysis_loader
        self._market_data_fetcher = market_data_fetcher
        self._transaction_cost = transaction_cost
        self._last_analysis: dict[str, Any] | None = None
        self._paper_journal = InMemoryJournal()
        self._semi_journal = InMemoryJournal()
        self._paper_engine = TradingEngine.for_paper_trading(
            risk_config=build_risk_config(semi_auto=False),
            journal=self._paper_journal,
            starting_cash=starting_cash,
        )
        self._semi_engine = TradingEngine.for_semi_auto(
            risk_config=build_risk_config(semi_auto=True),
            journal=self._semi_journal,
            starting_cash=starting_cash,
        )

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "list_strategies",
                "description": "List registered baseline strategy names.",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "get_market_data_status",
                "description": "Fetch market data metadata and freshness status.",
                "inputSchema": self._schema(
                    {
                        "symbol": {"type": "string"},
                        "timeframe": {"type": "string", "default": "1d"},
                        "period": {"type": "string", "default": "1mo"},
                    },
                    required=["symbol"],
                ),
            },
            {
                "name": "run_strategy_analysis",
                "description": "Run analysis/backtest and return a compact JSON-safe summary.",
                "inputSchema": self._schema(
                    {
                        "symbol": {"type": "string"},
                        "strategy": {"type": "string"},
                        "timeframe": {"type": "string", "default": "1d"},
                        "period": {"type": "string", "default": "1mo"},
                    },
                    required=["symbol", "strategy"],
                ),
            },
            {
                "name": "get_trade_lifecycle",
                "description": "Return the paper or semi-auto signal-to-portfolio lifecycle snapshot.",
                "inputSchema": self._schema(
                    {
                        "mode": {
                            "type": "string",
                            "enum": ["paper", "semi"],
                            "default": "paper",
                        }
                    }
                ),
            },
            {
                "name": "get_portfolio_snapshot",
                "description": "Replay journal events and return current portfolio state.",
                "inputSchema": self._schema(
                    {
                        "mode": {
                            "type": "string",
                            "enum": ["paper", "semi"],
                            "default": "paper",
                        }
                    }
                ),
            },
            {
                "name": "get_journal_events",
                "description": "Return append-only journal events for paper or semi-auto mode.",
                "inputSchema": self._schema(
                    {
                        "mode": {
                            "type": "string",
                            "enum": ["paper", "semi"],
                            "default": "paper",
                        },
                        "limit": {"type": "integer", "default": 20},
                    }
                ),
            },
            {
                "name": "simulate_order_intent",
                "description": "Create a paper or semi-auto intent from the latest analysis signal and run risk/order flow.",
                "inputSchema": self._schema(
                    {
                        "symbol": {"type": "string"},
                        "strategy": {"type": "string"},
                        "timeframe": {"type": "string", "default": "1d"},
                        "requested_quantity": {"type": "integer", "default": 10},
                        "mode": {
                            "type": "string",
                            "enum": ["paper", "semi"],
                            "default": "paper",
                        },
                    },
                    required=["symbol", "strategy"],
                ),
            },
        ]

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        arguments = arguments or {}
        dispatch = {
            "list_strategies": self._list_strategies,
            "get_market_data_status": self._get_market_data_status,
            "run_strategy_analysis": self._run_strategy_analysis,
            "get_trade_lifecycle": self._get_trade_lifecycle,
            "get_portfolio_snapshot": self._get_portfolio_snapshot,
            "get_journal_events": self._get_journal_events,
            "simulate_order_intent": self._simulate_order_intent,
        }
        if name not in dispatch:
            raise MCPToolError(f"Unknown MCP tool: {name}")
        return ensure_json_safe(dispatch[name](arguments))

    def format_tool_result(self, result: Any) -> dict[str, Any]:
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(ensure_json_safe(result), ensure_ascii=False),
                }
            ]
        }

    @staticmethod
    def _schema(properties: dict[str, Any], *, required: list[str] | None = None) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": properties,
            "required": required or [],
            "additionalProperties": False,
        }

    def _list_strategies(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return {"strategies": StrategyRegistry.get_available_strategies()}

    def _get_market_data_status(self, arguments: dict[str, Any]) -> dict[str, Any]:
        symbol = self._required(arguments, "symbol")
        timeframe = str(arguments.get("timeframe", "1d"))
        period = str(arguments.get("period", "1mo"))
        try:
            market_result = self._market_data_fetcher(symbol, period=period, interval=timeframe)
        except ControlledMarketDataError as exc:
            return {
                "ok": False,
                "symbol": exc.symbol,
                "attempted_source": exc.attempted_source,
                "fallback_attempted": exc.fallback_attempted,
                "diagnostics": exc.diagnostics,
                "message": str(exc),
            }
        return {
            "ok": True,
            "symbol": symbol,
            "timeframe": timeframe,
            "period": period,
            "source": market_result.source,
            "fallback_used": market_result.fallback_used,
            "warnings": market_result.warnings,
            "diagnostics": market_result.diagnostics,
            "data_freshness": market_result.data_freshness,
            "last_bar_time": market_result.last_bar_time,
            "is_stale": market_result.is_stale,
            "row_count": len(market_result.dataframe),
        }

    def _run_strategy_analysis(self, arguments: dict[str, Any]) -> dict[str, Any]:
        symbol = self._required(arguments, "symbol")
        strategy = self._required(arguments, "strategy")
        timeframe = str(arguments.get("timeframe", "1d"))
        period = str(arguments.get("period", "1mo"))
        result = self._analysis_loader(
            symbol=symbol,
            strategy_name=strategy,
            period=period,
            interval=timeframe,
            transaction_cost=self._transaction_cost,
        )
        self._last_analysis = result
        dataframe = result["df"]
        latest = dataframe.iloc[-1].to_dict()
        return {
            "symbol": symbol,
            "strategy": strategy,
            "timeframe": timeframe,
            "period": period,
            "metadata": result.get("metadata", {}),
            "kpi": result.get("kpi", {}),
            "latest_bar": latest,
            "latest_signal": int(latest.get("signal", 0)),
            "tail": dataframe_tail_records(dataframe, limit=5),
        }

    def _simulate_order_intent(self, arguments: dict[str, Any]) -> dict[str, Any]:
        symbol = self._required(arguments, "symbol")
        strategy = self._required(arguments, "strategy")
        timeframe = str(arguments.get("timeframe", "1d"))
        requested_quantity = int(arguments.get("requested_quantity", 10))
        mode = str(arguments.get("mode", "paper"))
        analysis = self._last_analysis
        if analysis is None:
            analysis = self._analysis_loader(
                symbol=symbol,
                strategy_name=strategy,
                period=str(arguments.get("period", "1mo")),
                interval=timeframe,
                transaction_cost=self._transaction_cost,
            )
            self._last_analysis = analysis

        signal = build_signal_from_analysis(
            analysis,
            symbol=symbol,
            strategy_name=strategy,
            timeframe=timeframe,
        )
        if signal is None:
            raise MCPToolError("No actionable signal found in the latest analysis.")

        engine = self._engine_for_mode(mode)
        execution_price = float(signal.metadata.get("reference_price", 0.0))
        outcome = engine.process_signal(
            signal,
            requested_quantity=requested_quantity,
            execution_price=execution_price,
        )
        return {
            "mode": mode,
            "intent": asdict(outcome.intent),
            "risk_decision": asdict(outcome.risk_decision),
            "order": asdict(outcome.order) if outcome.order is not None else None,
        }

    def _get_trade_lifecycle(self, arguments: dict[str, Any]) -> dict[str, Any]:
        mode = str(arguments.get("mode", "paper"))
        engine = self._engine_for_mode(mode)
        journal = self._journal_for_mode(mode)
        portfolio = engine.replay_portfolio(journal.read_all())
        snapshot = build_trade_lifecycle_view_model(
            journal_events=journal.read_all(),
            portfolio_state=portfolio,
        )
        return asdict(snapshot)

    def _get_portfolio_snapshot(self, arguments: dict[str, Any]) -> dict[str, Any]:
        mode = str(arguments.get("mode", "paper"))
        engine = self._engine_for_mode(mode)
        journal = self._journal_for_mode(mode)
        return asdict(engine.replay_portfolio(journal.read_all()))

    def _get_journal_events(self, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        mode = str(arguments.get("mode", "paper"))
        limit = int(arguments.get("limit", 20))
        events = self._journal_for_mode(mode).read_all()
        return [asdict(event) for event in events[-limit:]]

    def _engine_for_mode(self, mode: str) -> TradingEngine:
        if mode == "semi":
            return self._semi_engine
        if mode == "paper":
            return self._paper_engine
        raise MCPToolError(f"Unsupported mode: {mode}")

    def _journal_for_mode(self, mode: str) -> InMemoryJournal:
        if mode == "semi":
            return self._semi_journal
        if mode == "paper":
            return self._paper_journal
        raise MCPToolError(f"Unsupported mode: {mode}")

    @staticmethod
    def _required(arguments: dict[str, Any], key: str) -> str:
        value = arguments.get(key)
        if value in (None, ""):
            raise MCPToolError(f"Missing required argument: {key}")
        return str(value)
