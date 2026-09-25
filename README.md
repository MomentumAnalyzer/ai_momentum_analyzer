# ai_momentum_analyzer

MCP servers and agents for Trading Wiser. Momentum Analyzer, the application behind Trading Wiser, stays in its own private repository. This package does not contain that application. It talks to it over HTTP, and it ships the agent instructions that use those tools.

Trading Wiser and Momentum Analyzer are private. Only someone who has been explicitly onboarded and approved may use this MCP server or these agents. A wheel file or a checkout is not approval. See `LICENSE`.

## What you get

| Path | What it is |
| --- | --- |
| `mcp_servers/tradingwiser` | Stdio MCP server. Tools: `get_scan`, `get_signal_brief`, `get_prices`, `get_flow`, `get_unusual_options`, `get_unusual_volumes`, `get_unusual_rankings`, `get_sentiment`. |
| `mcp_servers/etrade` | How to connect a separate read-only E*TRADE MCP. This repo does not ship that server or any E*TRADE keys. |
| `agents/` | Agent instructions: daily holdings review, and the Trading Wiser signal critic. |

The signal critic's arithmetic step still runs inside a Momentum Analyzer checkout (`python -m momentum_analyzer.v2.cli.main critic`). That engine is not in this package. Without that checkout, the agent still uses the MCP tools and public market checks, and it says the recompute step was skipped.

## Install the package

Python 3.11 or newer.

```bash
pip install .
```

To hand the same thing to an approved user as a wheel:

```bash
python -m pip install build
python -m build
pip install dist/ai_momentum_analyzer-0.1.0-py3-none-any.whl
```

That installs two commands:

- `tradingwiser-mcp` — the MCP server process. Clients start it. You do not run it in a terminal.
- `ai-momentum-analyzer` — guided setup. It installs the MCP server, the agents, or both.

## Set up a client

```bash
ai-momentum-analyzer
```

The guide asks three things:

1. Install the MCP server, the agents, or both.
2. Which app: Cursor, Claude Desktop, Claude Code, or Codex.
3. For Cursor and Claude Code, this project only or every project for this user.

When you install the MCP server it asks for the Trading Wiser API base URL, username, and password (typed twice, not echoed). It writes them to `~/.config/ai-momentum-analyzer/secrets.json` with file mode `600`. The client MCP config receives only the path to that file, in `TRADINGWISER_SECRETS_FILE`. The password is not written into Cursor, Claude, or Codex config.

Reload MCP servers in the app after the command finishes. Then ask in normal language, for example "run my morning review" with a holdings screenshot, or "critique Trading Wiser on AAPL".

The same steps without the menu:

```bash
ai-momentum-analyzer install both --client cursor --target .
ai-momentum-analyzer install mcp --client claude-desktop
ai-momentum-analyzer install agents --client claude-code --target .
```

Add `--api-base` and `--username` to skip those two questions. The password is still a hidden prompt, or pass it with `--password-stdin` so it never appears in the shell history.

Claude Desktop does not load agent files. The installer still copies them into the project and tells you to paste the one you need into the Claude Project custom instructions.

### Where the MCP config is written

| Client | This project | All projects |
| --- | --- | --- |
| Cursor | `<project>/.cursor/mcp.json` | `~/.cursor/mcp.json` |
| Claude Code | `<project>/.mcp.json` | `~/.claude.json` |
| Claude Desktop | — | Claude's `claude_desktop_config.json` |
| Codex | — | `~/.codex/config.toml` |

Agents land in `.cursor/rules/` (Cursor), `.claude/agents/` (Claude Code), or `.codex/agents/` plus `AGENTS.md` when that file is not already there (Codex).

`examples/` shows the shape of those configs. The examples contain a path placeholder, not a password.

### Other MCP clients

VS Code, Windsurf, and Continue can use the same server. Point `command` at `tradingwiser-mcp` and set `TRADINGWISER_SECRETS_FILE` to the secrets file the installer created. See `examples/cursor.mcp.json`.

Perplexity works when it can start that local process. A connector that only accepts a remote HTTP MCP server cannot use this package. Do not paste the secrets file into a shared cloud config.

## E*TRADE holdings (optional)

The daily holdings agent can start from a pasted screenshot. A read-only E*TRADE MCP is optional and is not included. See `mcp_servers/etrade/README.md`. Order placement stays off. Those keys also stay in the client config only.

## Release

On the Actions tab, run **Release** and choose `minor` or `major`. The workflow is on `main`. From `0.1.0`, minor becomes `0.2.0` and major becomes `1.0.0`.

The run creates branch `release/vX.Y.Z`, commits that version in `pyproject.toml`, builds one wheel, and attaches it to the GitHub Release `vX.Y.Z`. It also opens a pull request into `main`.

```bash
pip install https://github.com/pranayVyas/ai_momentum_analyzer/releases/download/vX.Y.Z/ai_momentum_analyzer-X.Y.Z-py3-none-any.whl
```

That download still requires access to this repository. It does not grant access to Trading Wiser.

## Develop

```bash
python -m unittest mcp_servers.tradingwiser.test_client mcp_servers.tradingwiser.test_protocol
python scripts/test_bump_version.py
```

The protocol test speaks to a local stand-in. It uses the username `tester` and the password `tester-pass` against that stand-in only. Those are not Trading Wiser credentials.
