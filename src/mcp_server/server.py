from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .schemas import ensure_json_safe
from .tools import MCPToolError, MCPToolService

JSON_RPC_VERSION = "2.0"
SERVER_NAME = "stock-quant-mcp"
SERVER_VERSION = "0.1.0"


class MCPJsonRpcHandler:
    def __init__(self, *, service: MCPToolService) -> None:
        self._service = service

    def dispatch(self, payload: dict[str, Any]) -> dict[str, Any]:
        request_id = payload.get("id")
        method = payload.get("method")
        params = payload.get("params") or {}
        try:
            if method == "initialize":
                result = self._initialize()
            elif method == "tools/list":
                result = {"tools": self._service.list_tools()}
            elif method == "tools/call":
                name = params.get("name")
                arguments = params.get("arguments") or {}
                result = self._service.format_tool_result(
                    self._service.call_tool(name, arguments)
                )
            else:
                return self._error(request_id, -32601, f"Unknown MCP method: {method}")
            return {
                "jsonrpc": JSON_RPC_VERSION,
                "id": request_id,
                "result": ensure_json_safe(result),
            }
        except MCPToolError as exc:
            return self._error(request_id, -32602, str(exc))
        except Exception as exc:
            return self._error(request_id, -32603, f"Internal MCP error: {exc}")

    @staticmethod
    def _initialize() -> dict[str, Any]:
        return {
            "protocolVersion": "2024-11-05",
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            "capabilities": {"tools": {}},
        }

    @staticmethod
    def _error(request_id: object, code: int, message: str) -> dict[str, Any]:
        return {
            "jsonrpc": JSON_RPC_VERSION,
            "id": request_id,
            "error": {"code": code, "message": message},
        }


class MCPHttpRequestHandler(BaseHTTPRequestHandler):
    rpc_handler: MCPJsonRpcHandler

    def do_GET(self) -> None:
        if self.path.rstrip("/") not in {"", "/health"}:
            self._write_json(404, {"ok": False, "error": "Not found"})
            return
        self._write_json(200, {"ok": True, "name": SERVER_NAME})

    def do_POST(self) -> None:
        if self.path.rstrip("/") != "/mcp":
            self._write_json(404, {"ok": False, "error": "Use POST /mcp"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self._write_json(
                400,
                {
                    "jsonrpc": JSON_RPC_VERSION,
                    "id": None,
                    "error": {"code": -32700, "message": "Invalid JSON"},
                },
            )
            return
        self._write_json(200, self.rpc_handler.dispatch(payload))

    def log_message(self, format: str, *args: object) -> None:
        return

    def _write_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(ensure_json_safe(payload), ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def build_server(host: str, port: int) -> ThreadingHTTPServer:
    service = MCPToolService()
    rpc_handler = MCPJsonRpcHandler(service=service)

    class BoundMCPHttpRequestHandler(MCPHttpRequestHandler):
        pass

    BoundMCPHttpRequestHandler.rpc_handler = rpc_handler
    return ThreadingHTTPServer((host, port), BoundMCPHttpRequestHandler)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the stock quant MCP server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    args = parser.parse_args()

    server = build_server(args.host, args.port)
    print(f"MCP server listening on http://{args.host}:{args.port}/mcp")
    server.serve_forever()


if __name__ == "__main__":
    main()
