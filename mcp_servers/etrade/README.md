# E*TRADE MCP (read-only holdings source)

The [daily holdings review agent](../../agents/daily-holdings-review.mdc)
can pull its start-of-day snapshot from a **read-only** E*TRADE MCP server
instead of a manual screenshot. This repo does **not** ship an E*TRADE server.
Connect an existing, reviewed one in your own MCP client (Cursor, Claude, or
Codex). The server runs locally and talks only to E*TRADE's official OAuth API.

## Which server

The agent only needs cash, balances, and positions — reads, never orders.

| Server | Holdings? | Write surface | Verdict |
| --- | --- | --- | --- |
| `t11z/etrade-mcp` | yes: accounts, balances, portfolio, transactions | None (reads only) | Preferred — smallest surface. Unaffiliated; intended for single-user local use against your own account. |
| `sblattj/etrade-mcp` | yes: account reads | Can place orders (off by default) | Acceptable only with order placement left disabled. |
| `jjmerri/etrade-mcp` | no: quotes / option chains only | — | Cannot supply holdings. |
| `ohenak/etrade-mcp` | no: quotes / option chains only | — | Cannot supply holdings. |

## Connect it (client config — keep secrets out of this repo)

Add the server to your client's MCP settings, not to a file in this repo. The
E*TRADE consumer key, secret, and OAuth tokens live only in that private client
config. Example shape (placeholders only; use the chosen server's README for
exact env names and the OAuth flow):

```json
{
  "mcpServers": {
    "etrade": {
      "command": "<per the server README, e.g. uvx / npx / python>",
      "args": ["<server entry point>"],
      "env": {
        "ETRADE_CONSUMER_KEY": "set-in-the-client-config-only",
        "ETRADE_CONSUMER_SECRET": "set-in-the-client-config-only",
        "ETRADE_ENV": "sandbox"
      }
    }
  }
}
```

E*TRADE uses OAuth 1.0a with a browser verification step and offers a sandbox
environment. Validate against sandbox first, then switch to production.

## Safety checklist

- [ ] Server is a reviewed, pinned commit run locally.
- [ ] Source and dependencies do not phone home or send telemetry. Account data stays between your machine and E*TRADE.
- [ ] Only read tools are enabled. If the server can place orders, order placement is disabled.
- [ ] Credentials live in the client MCP config only — never in this repo, a committed file, logs, or chat.
- [ ] The agent's safety rules hold: no positions, balances, dollar amounts, or account identifiers go into web search or any third party.

If any box can't be checked, fall back to a manual paste of the snapshot.
