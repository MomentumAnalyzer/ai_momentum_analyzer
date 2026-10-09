# Momentum Analyzer plugin

Momentum Analyzer is the product. Trading Wiser is the company that publishes it.

This repo is the installable plugin for the official marketplaces. It points at the
hosted MCP server and nothing else:

```json
{
  "mcpServers": {
    "momentum-analyzer": {
      "url": "https://momentum-analyzer.com/mcp"
    }
  }
}
```

There is no local server, no skills bundle, no credentials, and no app code in this repo.
Auth happens on `momentum-analyzer.com` when the user connects.

## Files

| Path | Purpose |
| --- | --- |
| `plugin.json` | Portable Agent Plugin manifest (Cursor, OpenAI). |
| `mcp.json` | Hosted MCP entry shared by Cursor and OpenAI. |
| `.cursor-plugin/plugin.json` | Cursor Marketplace manifest. |
| `.claude-plugin/plugin.json` | Claude plugin manifest. |
| `.mcp.json` | Claude Code plugin MCP entry. |

## Install (local test)

Cursor: copy this repo to `~/.cursor/plugins/local/momentum-analyzer` and enable it.
Claude Code: add this repo as a plugin source and install `momentum-analyzer`.
OpenAI: build a ZIP of this repo (MCP included) and upload it in the Plugins page.

## Listings

- **Cursor Marketplace:** submit the public repo URL at
  [cursor.com/marketplace/publish](https://cursor.com/marketplace/publish). Manual review.
- **Claude:** submit the plugin bundle at
  [claude.ai/directory/manage](https://claude.ai/directory/manage), plus the hosted
  server as an MCP connector. Repo must be public before it goes live.
- **OpenAI (ChatGPT + Codex):** verify the publisher, upload the ZIP with the MCP
  included, connect `https://momentum-analyzer.com/mcp`, serve the domain challenge at
  `https://momentum-analyzer.com/.well-known/openai-apps-challenge`, and provide a demo
  login. Publish only after approval.

Only onboarded, approved users may use the hosted service. See [LICENSE](LICENSE).
