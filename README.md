# Professional Quant Trading Workspace

This repository is a Python-based **Professional Quant Trading Workspace**. 
It has evolved from a simple technical-analysis prototype into a structured, maintainable quant platform with explicit boundaries for market data, strategy, risk, order lifecycle, portfolio management, and UI.

## Core Capabilities

- **Paper Trading Core**: A complete execution simulation environment mapping `Signal → Intent → Risk → Order → Fill → Portfolio`.
- **Live-first Market Data with Fallback**: Resilient data fetching with built-in metadata tracking (LIVE, DELAYED, LOCAL_CACHE, STALE) to ensure system reliability.
- **Selection / Ranking Flow**: Filtering and ranking mechanisms to upgrade raw signals into actionable trade intents based on regime and setup scoring.
- **Research / Scenario Projection**: Research-driven scenario projection and risk-aware decision support (AI Projection), decoupled from strict buy/sell recommendations.
- **OMS-style UI**: A trading lifecycle panel providing visibility into Open Orders, Recent Fills, Position snapshots, and Journal events.

---

## Architecture Blueprint

The system follows a layered, interface-driven design (SRP & SoC):

```text
src/
├─ app_services/      Thin application orchestration & session state management
├─ config/            Centralized and versioned configuration
├─ domain/            Pure domain contracts (e.g., IPredictor)
├─ mcp_server/        MCP-compatible HTTP JSON-RPC adapter for agent integration
├─ market_data/       Live/Local providers, caching backend, and data status normalization
├─ selection/         Regime, scoring, ranking, sizing, intent factory
├─ trading/           Paper trading core (RiskManager, Executor, Portfolio, Journal)
├─ ui/                Streamlit components and OMS-style workspace pages
└─ tests/             Unit and integration tests for CI pipelines
```

The target dependency direction is strictly:
`UI / MCP / App Services -> Domain Interfaces -> Trading / Selection / Market Data Services -> Infrastructure Adapters`

## Project Tooling & CI

We use modern Python tooling to ensure repository hygiene and maintainability:
- **Formatting**: `black`
- **Linting**: `ruff`
- **Testing**: `pytest`

A `pyproject.toml` is included to standardize these tools across environments, and a GitHub Actions workflow enforces quality on push.

## Quick Start

### 1. Install Dependencies

```powershell
py -m pip install -r requirements.txt
```

### 2. Verify System Integrity

```powershell
py -m pytest -v
```

### 3. Launch the Trading Workspace

```powershell
py -m streamlit run app.py
```

## Product Positioning

This platform is intentionally positioned as a:
- **Trading Workspace**: For research, signal generation, and order lifecycle management.
- **Risk-Aware Decision Support**: Focusing on exposure limits and position sizing.
- **Paper Trading Engine**: A safe environment to validate quant models before live execution.

**Disclaimer**: This system is *not* a guaranteed AI price prediction engine, *not* a black-box buy/sell recommendation tool, and *not* currently wired to a production brokerage for live automated trading. Live execution is out of scope until risk, audit, and reconciliation layers are fully formalized.

---

*This README was updated to reflect the transition into a commercial-grade quantitative trading platform architecture.*
