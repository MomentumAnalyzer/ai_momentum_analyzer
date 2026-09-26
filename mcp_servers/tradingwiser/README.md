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

`get_scan`, `get_signal_brief`, `get_signal_briefs`, `get_prices`, `get_indicators`, `get_fundamentals`, `get_zones`, `get_trend_history`, `get_flow`, `get_unusual_options`, `get_unusual_volumes`, `get_unusual_rankings`, `get_sentiment`, `get_key_dates`, `get_market_sentiment`.

`get_key_dates` needs no symbol. Upcoming events run from today through the next 21 days, and realized events are the recent prints. `get_market_sentiment` is the Fed and macro snapshot. Per-symbol sector headlines stay inside `get_sentiment`. Open-versus-close inference is the `inferred_action` field on `get_unusual_options`. `get_signal_brief` is the latest brief. `get_signal_briefs` is the history.
