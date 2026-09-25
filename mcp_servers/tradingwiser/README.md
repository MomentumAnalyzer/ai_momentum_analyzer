# Trading Wiser MCP

Stdio MCP server for the Trading Wiser HTTP API. Cursor, Claude Desktop, Claude Code, and Codex start this process from their MCP settings. You do not run it in a separate terminal.

The server calls `POST /api/v3/auth/login` and then the read routes. If the username, password, or base URL is missing, or login is rejected, it does not call a data route. The same login is required for a direct call to `/api/v3`. The MCP source does not grant access.

After `pip install` of this package, run `ai-momentum-analyzer` and choose the MCP server. It asks for the API base URL, username, and password, stores them in `~/.config/ai-momentum-analyzer/secrets.json`, and writes a client config that only contains the path:

```json
{
  "mcpServers": {
    "tradingwiser": {
      "command": "tradingwiser-mcp",
      "env": {
        "TRADINGWISER_SECRETS_FILE": "/home/you/.config/ai-momentum-analyzer/secrets.json"
      }
    }
  }
}
```

The password is not in the client config and not in this repo. See `examples/`.

## Tools

`get_scan`, `get_signal_brief`, `get_prices`, `get_flow`, `get_unusual_options`, `get_unusual_volumes`, `get_unusual_rankings`, `get_sentiment`.

There is no separate headlines route. Sector headlines are inside `get_sentiment` when the API snapshot includes them. Open-versus-close inference is the `inferred_action` field on `get_unusual_options`.
