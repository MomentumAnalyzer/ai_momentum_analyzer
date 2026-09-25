"""Trading Wiser MCP server.

Stdio transport so Cursor, Claude, and Codex can launch the same process.
Tools call the Trading Wiser HTTP API. They do not open a database connection.
"""

from __future__ import annotations

import json
import sys
from typing import Any

from mcp_servers.tradingwiser.client import AuthError, TradingWiserClient

SERVER_NAME = "tradingwiser"
PROTOCOL = "2024-11-05"

TOOLS = [
    {
        "name": "get_scan",
        "description": "Latest grade, conviction, pillars, entry, stop, and target for one symbol.",
        "path": "/api/v3/ticker/{symbol}/scan",
        "symbol": True,
    },
    {
        "name": "get_signal_brief",
        "description": "Latest signal brief for one symbol.",
        "path": "/api/v3/ticker/{symbol}/signal-brief",
        "symbol": True,
    },
    {
        "name": "get_prices",
        "description": "Recent daily prices for one symbol.",
        "path": "/api/v3/ticker/{symbol}/prices",
        "symbol": True,
        "query": ["days"],
    },
    {
        "name": "get_flow",
        "description": "Options flow summary for one symbol.",
        "path": "/api/v3/ticker/{symbol}/flow",
        "symbol": True,
    },
    {
        "name": "get_unusual_options",
        "description": "Session unusual contracts, scores, greeks, and inferred open/close action.",
        "path": "/api/v3/ticker/{symbol}/options-unusual",
        "symbol": True,
        "query": ["date", "view"],
    },
    {
        "name": "get_unusual_volumes",
        "description": "Strikes whose volume is elevated versus the recent average.",
        "path": "/api/v3/ticker/{symbol}/unusual-volumes",
        "symbol": True,
        "query": ["option_type"],
    },
    {
        "name": "get_unusual_rankings",
        "description": "Watchlist names ranked by unusual options activity.",
        "path": "/api/v3/options-unusual/rankings",
        "symbol": False,
        "query": ["date", "bucket", "limit"],
    },
    {
        "name": "get_sentiment",
        "description": "Sector sentiment snapshot for one symbol, including stored headlines when present.",
        "path": "/api/v3/ticker/{symbol}/sentiment",
        "symbol": True,
    },
]


def _tool_schema(spec: dict) -> dict:
    props: dict[str, Any] = {}
    required: list[str] = []
    if spec["symbol"]:
        props["symbol"] = {"type": "string", "description": "Ticker symbol"}
        required.append("symbol")
    for name in spec.get("query", []):
        props[name] = {"type": "string"}
    return {
        "name": spec["name"],
        "description": spec["description"],
        "inputSchema": {"type": "object", "properties": props, "required": required},
    }


def _read_message() -> dict | None:
    """Read one JSON-RPC message.

    Cursor sends one JSON object per line. Older clients send a
    Content-Length header and then the body.
    """
    line = sys.stdin.buffer.readline()
    if not line:
        return None
    stripped = line.strip()
    if not stripped:
        return _read_message()
    if stripped.lower().startswith(b"content-length:"):
        length = int(stripped.split(b":", 1)[1].strip())
        while True:
            blank = sys.stdin.buffer.readline()
            if blank in (b"\r\n", b"\n", b""):
                break
        body = sys.stdin.buffer.read(length)
        return json.loads(body.decode())
    return json.loads(stripped.decode())


def _write_message(payload: dict) -> None:
    sys.stdout.buffer.write(json.dumps(payload).encode() + b"\n")
    sys.stdout.buffer.flush()


def _call_tool(client: TradingWiserClient, name: str, arguments: dict) -> dict:
    spec = next(item for item in TOOLS if item["name"] == name)
    symbol = str(arguments.get("symbol", "")).upper().strip()
    if spec["symbol"] and not symbol:
        raise AuthError("symbol is required")
    path = spec["path"].format(symbol=symbol)
    query = {key: arguments.get(key) for key in spec.get("query", [])}
    return client.get_json(path, query)


def _handle(message: dict, client: TradingWiserClient | None) -> TradingWiserClient | None:
    method = message.get("method")
    msg_id = message.get("id")
    if method == "notifications/initialized":
        return client
    if msg_id is None:
        return client
    if method == "initialize":
        _write_message(
            {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": PROTOCOL,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": SERVER_NAME, "version": "0.1.0"},
                },
            }
        )
        return client
    if method == "tools/list":
        _write_message(
            {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"tools": [_tool_schema(spec) for spec in TOOLS]},
            }
        )
        return client
    if method == "tools/call":
        params = message.get("params") or {}
        name = params.get("name")
        arguments = params.get("arguments") or {}
        try:
            if client is None:
                client = TradingWiserClient.from_env()
            if not any(spec["name"] == name for spec in TOOLS):
                raise AuthError(f"Unknown tool: {name}")
            payload = _call_tool(client, name, arguments)
            text = json.dumps(payload)
            is_error = False
        except AuthError as exc:
            text = str(exc)
            is_error = True
            client = None
        _write_message(
            {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": text}],
                    "isError": is_error,
                },
            }
        )
        return client
    _write_message(
        {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }
    )
    return client


def main() -> int:
    client: TradingWiserClient | None = None
    while True:
        message = _read_message()
        if message is None:
            return 0
        client = _handle(message, client)


if __name__ == "__main__":
    sys.exit(main())
