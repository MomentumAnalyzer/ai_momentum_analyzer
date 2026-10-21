<p align="center">
  <img src="assets/logo.png" alt="Momentum Analyzer logo" width="120" height="120">
</p>

<h1 align="center">Momentum Analyzer</h1>

<p align="center">
  Graded stock research, delivered to your agent over MCP.<br>
  A product of <strong>Trading Wiser</strong> · <a href="https://momentum-analyzer.com">momentum-analyzer.com</a>
</p>

> [!IMPORTANT]
> **Research and learning only. This is not financial, investment, or trading advice.**
> Momentum Analyzer does not connect to any broker, does not place, size, or execute trades,
> and makes no claims about returns or performance. Review everything yourself before any trade.

## What it is

Momentum Analyzer is a hosted, read-only MCP server for stock and ETF research. It reads price
action, institutional options flow, and structural trend across 5, 10, 20, 50, and 252-day
windows. For each symbol on an admin-maintained watchlist, it publishes a conviction score from
0 to 100 and a grade of A+, A, B, or C. The score blends four pillars: technical (30%), options
flow (30%), fundamentals (20%), and price/momentum (20%). Your agent (Claude, Cursor, Codex,
Grok, or any MCP client that supports remote servers with OAuth) connects to
`https://momentum-analyzer.com/mcp` and signs in through the browser. You don't install or run
anything. This repository holds only the plugin manifests and docs that point at that hosted
endpoint. It contains no server code and no credentials.

## What you can ask it

All tools are read-only (OAuth scope `market-data:read`).

**Graded setups**
- The latest grade, conviction score, pillar breakdown, and reference entry/stop/target levels for a symbol (`get_scan`)
- The latest signal brief for a symbol, or its brief history (`get_signal_brief`, `get_signal_briefs`)
- Support, resistance, and balance zones (`get_zones`)
- A fundamentals snapshot (`get_fundamentals`)

**Options flow**
- The options-flow pillar read for a symbol (`get_flow`)
- Contracts building unusual open interest (`get_unusual_options`)
- Strikes with volume elevated versus their recent average (`get_unusual_volumes`)
- Watchlist names ranked by the latest options-session read (`get_unusual_rankings`)

**Multi-window trend and market context**
- Recent daily prices, plus daily or weekly technical indicators including relative volume (`get_prices`, `get_indicators`)
- Daily trend snapshots: phase, conviction, and volume participation (`get_trend_history`)
- Sector sentiment with stored headlines, and the latest Fed and macro sentiment (`get_sentiment`, `get_market_sentiment`)
- Upcoming key economic dates and recent realized events (`get_key_dates`)

**Paper-only strategy books (learning only)**
- Daily and weekly paper strategy books (`get_strategy_daily_slow`, `get_strategy_daily_volume`,
  `get_strategy_weekly_slow`, `get_strategy_weekly_volume`). These are simulated, paper-only
  records for studying how rules behave. They are not a track record and not a recommendation.

Example prompts:
- "What's the current Momentum Analyzer grade and brief for MSFT, and which pillar is weakest?"
- "Show unusual options activity for NVDA and the support and resistance zones nearby."
- "How has the trend phase for SPY changed over the last 20 sessions?"

The [setup page](https://momentum-analyzer.com/setup) also describes three agent-side workflows
(daily holdings review, signal critic, zone analysis). These run in your agent, use Momentum
Analyzer as a prior, and never place trades.

## Quick setup

Endpoint: **`https://momentum-analyzer.com/mcp`** (remote, Streamable HTTP, OAuth with PKCE)

Sign-in always happens in your browser on momentum-analyzer.com, and the client keeps an OAuth
token. **Never put your password in a client config.**
[Create a free account](https://momentum-analyzer.com/register) first, or create one during sign-in.

### Claude

- **Claude (web or desktop):** Settings → Connectors → *Add custom connector*, paste
  `https://momentum-analyzer.com/mcp`, then complete sign-in in the browser.
- **Claude Code:**
  ```bash
  claude mcp add --transport http ma https://momentum-analyzer.com/mcp
  ```
  The browser sign-in starts the first time a tool is used (or run `/mcp` to authenticate).
- **Claude Code plugin:** this repo is a plugin marketplace:
  ```text
  /plugin marketplace add MomentumAnalyzer/ai_momentum_analyzer
  /plugin install momentum-analyzer@momentum-analyzer
  ```

### Cursor

Add a remote MCP server in Cursor Settings → MCP, or put this in `~/.cursor/mcp.json`
(global) or `.cursor/mcp.json` (project):

```json
{
  "mcpServers": {
    "ma": {
      "url": "https://momentum-analyzer.com/mcp"
    }
  }
}
```

Save, then approve the browser sign-in.

### Any other MCP client (Codex, Grok, and others)

Add a remote (HTTP) MCP server with the URL `https://momentum-analyzer.com/mcp` and complete
OAuth in the browser. Clients that use the common `mcpServers` format can use the same block:

```json
{
  "mcpServers": {
    "ma": {
      "type": "http",
      "url": "https://momentum-analyzer.com/mcp"
    }
  }
}
```

The server supports OAuth 2.x authorization code with PKCE (S256), refresh tokens, and dynamic
client registration. An unauthenticated request returns `401` with `resource_metadata`, so
OAuth-aware clients discover sign-in automatically. It is also listed in the
[Official MCP Registry](https://registry.modelcontextprotocol.io/v0/servers?search=com.momentum-analyzer)
as `com.momentum-analyzer/momentum-analyzer`.

## Plans

**Free (live)**
- New accounts are active immediately.
- 7 days of the full watchlist over MCP, then only symbols marked free.
- 60 days of prices, indicators, and trend history.
- 20 MCP calls per minute and 200 MCP calls per day (America/New_York day).
- No dashboard on the free plan.

**Paid (coming soon)**
- Automated subscription is coming soon. Until then, email us to be onboarded.

Details: [momentum-analyzer.com/pricing](https://momentum-analyzer.com/pricing) ·
Coverage: [momentum-analyzer.com/coverage](https://momentum-analyzer.com/coverage)

## Privacy and data

Momentum Analyzer is read-only. It never asks for brokerage credentials and never connects to a
broker. Your password stays on momentum-analyzer.com, and MCP clients hold only an OAuth token
you can revoke. A full privacy policy is coming soon.

## Support

Questions, onboarding, or problems: **support.ma@momentum-analyzer.com**
Updates: [@MomentumMCP on X](https://x.com/MomentumMCP)

## Disclaimer

Momentum Analyzer provides research and educational information only. It is **not financial,
investment, or trading advice**, and Trading Wiser does not provide investment recommendations.
It does not connect to brokers and does not place, size, or execute trades. Grades, scores,
levels, and paper strategy books describe past and current data. They are not predictions, and
no returns or performance are claimed or implied. All trading involves risk, including the loss
of capital. Do your own review, and consult a qualified financial advisor before making
investment decisions. See the [Terms & Conditions](https://momentum-analyzer.com/terms).

## License

Proprietary. © 2026 Trading Wiser. All rights reserved. This repository is not open source.
Use of the hosted service is governed by the [Terms & Conditions](https://momentum-analyzer.com/terms).
See [LICENSE](LICENSE).
