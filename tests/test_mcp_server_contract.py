from __future__ import annotations

import json

from src.mcp_server.server import MCPJsonRpcHandler
from src.mcp_server.tools import MCPToolService


def _dispatch(payload: dict) -> dict:
    service = MCPToolService(analysis_loader=lambda **_: {})
    return MCPJsonRpcHandler(service=service).dispatch(payload)


def test_mcp_initialize_returns_server_capabilities() -> None:
    response = _dispatch({"jsonrpc": "2.0", "id": 1, "method": "initialize"})

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert response["result"]["serverInfo"]["name"] == "stock-quant-mcp"
    assert "tools" in response["result"]["capabilities"]


def test_mcp_tools_list_uses_mcp_content_shape() -> None:
    response = _dispatch({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})

    tool_names = {tool["name"] for tool in response["result"]["tools"]}
    assert "list_strategies" in tool_names


def test_mcp_tools_call_returns_text_content() -> None:
    response = _dispatch(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "list_strategies", "arguments": {}},
        }
    )

    content = response["result"]["content"][0]
    assert content["type"] == "text"
    parsed = json.loads(content["text"])
    assert "strategies" in parsed


def test_mcp_unknown_tool_returns_json_rpc_error() -> None:
    response = _dispatch(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "submit_live_order", "arguments": {}},
        }
    )

    assert response["error"]["code"] == -32602
    assert "Unknown MCP tool" in response["error"]["message"]
