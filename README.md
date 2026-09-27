# ai_momentum_analyzer

Trading Wiser's local MCP server and portable Agent Skills. Momentum Analyzer remains in its own private repository; this package connects to it over HTTP and provides repeatable workflows for AI clients.

Trading Wiser and Momentum Analyzer are private. Only explicitly onboarded and approved users may use this package. Installing a wheel or plugin does not grant service access. See [LICENSE](LICENSE).

## Package contents

| Path | Purpose |
| --- | --- |
| `mcp_servers/tradingwiser/` | Local stdio MCP server for Trading Wiser data. |
| `skills/daily-holdings-review/` | Guided holdings review. |
| `skills/tw-signal-critic/` | Compare a Trading Wiser signal with public market data. |
| `skills/zone-analysis-report/` | Defined support / resistance workflow and fixed HTML report renderer. |
| `plugin.json` | Portable Agent Plugin manifest for Codex and Cursor. |
| `.claude-plugin/plugin.json` | Claude Code plugin manifest for the same skills. |

The shared foundation is Agent Skills plus MCP. Plugin manifests are optional installation wrappers: Codex and Cursor accept the portable Agent Plugin format, while Claude Code uses its own plugin manifest. The plugin packages in this repository install the skills; set up MCP with the guided installer so credentials stay in a private local file.

## Install

Python 3.11 or newer:

```bash
pip install .
ai-momentum-analyzer
```

The guided installer asks whether to install the MCP server, skills, or both; which client; and whether skills should apply to this project or the user account. Credentials are requested only for MCP setup and stored in `~/.config/ai-momentum-analyzer/secrets.json` with restrictive permissions. Client configuration contains only the path to that file.

Non-interactive examples:

```bash
ai-momentum-analyzer install both --client cursor --target .
ai-momentum-analyzer install both --client codex --target .
ai-momentum-analyzer install both --client claude-code --target .
ai-momentum-analyzer install both --client claude-desktop
```

Add `--scope user` to install skills for the user account instead of the project. Codex's MCP connection is user-level; its skills can still be project-level. The legacy `install agents` and `install-agents` commands remain aliases for installing skills.

### Where skills and MCP are installed

| Client | Project skills | User skills | MCP configuration |
| --- | --- | --- | --- |
| Cursor | `.agents/skills/` | `~/.agents/skills/` | `.cursor/mcp.json` or `~/.cursor/mcp.json` |
| Codex | `.agents/skills/` | `~/.agents/skills/` | `~/.codex/config.toml` |
| Claude Code | `.claude/skills/` | `~/.claude/skills/` | `.mcp.json` or `~/.claude.json` |
| Claude Desktop / Claude app | Upload generated skill ZIPs in **Customize → Skills** | Skills are account-level | Claude's desktop MCP config |

Claude Desktop does not load local skill folders. The installer creates an upload-ready plugin ZIP and individual skill ZIPs under `tradingwiser-claude-skills/`. The plugin ZIP is the easiest option: upload it under **Customize → Plugins → Add → Upload a custom plugin**. The individual ZIPs can be uploaded under **Customize → Skills**. Claude Code loads skills from `.claude/skills/` or its Claude plugin. Claude app skills require code execution / file creation to be enabled.

Cursor and Codex can install the repository as a plugin using the root `plugin.json`; Claude uses `.claude-plugin/plugin.json`. Plugin installation supplies skills only. Run `ai-momentum-analyzer install mcp --client <client>` once to configure Trading Wiser access. Do not put passwords or secrets files in a plugin or project repository.

## Zone report consistency

The zone-analysis skill prescribes a phased workflow, an explicit source policy, a JSON report schema, and one report per ticker. It then calls the bundled renderer instead of asking the model to author HTML. The renderer controls section order, styling, number display, missing-value labels, rejection-rate calculation, escaping, and the public-market verdict. Narrative judgments can still vary with the model and input data; the layout and deterministic calculations do not.

Report assets are in `skills/zone-analysis-report/assets/`. To render a report data file manually:

```bash
python3 skills/zone-analysis-report/scripts/render_report.py report.json --output NVDA_detailed_zone_analysis.html
```

The skill guides the model to use only the named Trading Wiser MCP tools and the specified public check. A skill cannot technically disable other tools in a client; strict source isolation also requires restricting that client's enabled tools.

## Other MCP clients

VS Code, Windsurf, and Continue can launch `tradingwiser-mcp` with `TRADINGWISER_SECRETS_FILE` pointing at the secrets file. See [`examples/cursor.mcp.json`](examples/cursor.mcp.json). Perplexity can use the package only when it can launch a local stdio MCP process.

## E*TRADE holdings (optional)

The holdings skill can start from a pasted screenshot. A read-only E*TRADE MCP is optional and is not included. See [`mcp_servers/etrade/README.md`](mcp_servers/etrade/README.md). Order placement stays off.

## Release

On the Actions tab, run **Release** and choose `minor` or `major`. The workflow builds one wheel and attaches it to the GitHub Release. The source repository and download remain private; a release does not grant access to Trading Wiser.

## Develop

The MCP protocol examples and installer checks are in the repository. To inspect the available commands:

```bash
ai-momentum-analyzer --help
```
