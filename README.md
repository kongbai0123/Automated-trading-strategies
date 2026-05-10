# Professional Quant Trading Workspace

This repository is a Python-based trading research and paper-trading workspace.
It is being refactored from an early technical-analysis prototype into a more
maintainable quant platform with explicit market data, strategy, risk, order
lifecycle, portfolio, journal, UI, and MCP boundaries.

The current system is not a live brokerage execution platform and should not be
treated as investment advice. Predictor output is scenario projection and
risk-aware research support, not a buy/sell instruction.

## Current Scope

- Market data loading with live-first Yahoo Finance fallback handling
- Technical indicators: SMA, RSI, MACD, ATR
- Baseline strategies: RSI/MACD, moving-average crossover, Bollinger breakout
- Backtest pipeline with KPI calculation
- Paper trading core with signal, intent, risk, order, fill, portfolio, and journal events
- Trading workspace UI built with Streamlit and Plotly
- Trade lifecycle panel for OMS-style visibility
- MCP server adapter for agent access to read, analysis, journal, portfolio, and paper-safe tools
- Predictor domain layer with `IPredictor`, `HeuristicPredictor`, `ProjectionResult`, and `PredictorConfig`

## Architecture

```text
src/
├─ app_services/      Application orchestration for UI workflows
├─ config/            Versioned configuration models
├─ domain/            Pure domain contracts and value objects
├─ mcp_server/        MCP-compatible HTTP JSON-RPC adapter
├─ selection/         Regime, scoring, ranking, sizing, intent factory
├─ trading/           Paper trading core, risk, portfolio, orders, journal
├─ ui/                Streamlit components and workspace pages
├─ market_data.py     Live-first market data service with fallback metadata
├─ ui_pipeline.py     Analysis pipeline boundary
└─ predictor.py       Legacy compatibility predictor facade
```

The target dependency direction is:

```text
UI / MCP / App Services
-> Domain interfaces
-> Trading / Selection / Market data services
-> Infrastructure adapters
```

## Predictor Layer

The new predictor layer is intentionally conservative:

- `IPredictor` defines the domain contract.
- `HeuristicPredictor` implements deterministic ATR/SMA/MACD scenario projection.
- `PredictorConfig` centralizes thresholds, weights, and validation settings.
- `ProjectionResult` is an immutable output value object.

This layer is for research and decision support only. Future ML predictors should
implement the same `IPredictor` interface instead of changing UI or application
services directly.

## MCP Server

Run locally:

```powershell
py -m src.mcp_server.server --host 127.0.0.1 --port 8765
```

Endpoint:

```text
http://127.0.0.1:8765/mcp
```

Public HTTPS requires deployment behind TLS:

```text
https://<your-domain>/mcp
```

MCP-1 exposes read, analysis, journal, portfolio, and paper-safe tools. It does
not expose live broker order placement.

## Quick Start

Install dependencies:

```powershell
py -m pip install -r requirements.txt
```

Run tests:

```powershell
py -m pytest -v
```

Run the Streamlit workspace:

```powershell
py -m streamlit run app.py
```

## Development Checks

Format and lint:

```powershell
py -m black app.py src tests
py -m ruff check app.py src tests --fix --no-cache
```

## Product Positioning

This project should be described as:

- Trading decision workspace
- Scenario projection
- Risk-aware decision support
- Paper trading and order lifecycle research
- Quant platform architecture prototype

Avoid describing the system as:

- Guaranteed AI price prediction
- Strong buy/sell recommendation engine
- Live trading automation
- Production brokerage execution system

## Roadmap

Near-term priorities:

- Connect legacy `src/predictor.py` to the new domain predictor layer through a compatibility adapter
- Add experiment metadata: `run_id`, config snapshot, dataset hash, data source, and timestamp
- Continue thinning `app.py` into application services
- Expand strategy metadata and registry validation
- Keep live broker execution out of scope until risk, audit, auth, and broker reconciliation are formalized

