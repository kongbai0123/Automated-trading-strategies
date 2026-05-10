# MCP Server

This project exposes a first-phase MCP-compatible HTTP JSON-RPC endpoint for
agent access to the quant trading workspace.

## Scope

MCP-1 is limited to read, analysis, journal, portfolio, and paper/semi-auto-safe
tools. It does not expose live broker execution.

Available tools:

- `list_strategies`
- `get_market_data_status`
- `run_strategy_analysis`
- `get_trade_lifecycle`
- `get_portfolio_snapshot`
- `get_journal_events`
- `simulate_order_intent`

## Run Locally

```powershell
py -m src.mcp_server.server --host 127.0.0.1 --port 8765
```

Local endpoint:

```text
http://127.0.0.1:8765/mcp
```

Health check:

```text
http://127.0.0.1:8765/health
```

## JSON-RPC Examples

Initialize:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize"
}
```

List tools:

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/list"
}
```

Call a tool:

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "run_strategy_analysis",
    "arguments": {
      "symbol": "2330.TW",
      "strategy": "RSI_MACD",
      "timeframe": "1d",
      "period": "1mo"
    }
  }
}
```

## HTTPS Endpoint

The local server is plain HTTP by design. For a public MCP URL, deploy this
server behind a TLS reverse proxy or platform that terminates HTTPS.

Expected public MCP path:

```text
https://<your-domain>/mcp
```

Do not expose live order placement through this endpoint until broker
authentication, user authorization, audit policy, and risk gates are formalized.
