"""Interactive setup for the Trading Wiser MCP server and agents.

The password is written only to a secrets file outside the project. MCP client
configs store the path to that file, not the password.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import shutil
import sys
from importlib.resources import files
from pathlib import Path
from urllib.parse import urlparse

CLIENTS = ("cursor", "claude-desktop", "claude-code", "codex")
AGENT_DIRS = {
    "cursor": Path(".cursor") / "rules",
    "claude-code": Path(".claude") / "agents",
    "claude-desktop": Path(".claude") / "agents",
    "codex": Path(".codex") / "agents",
}
SECRETS_NAME = "secrets.json"


def secrets_path() -> Path:
    return Path.home() / ".config" / "ai-momentum-analyzer" / SECRETS_NAME


def write_secrets(path: Path, api_base: str, username: str, password: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"api_base": api_base.rstrip("/"), "username": username, "password": password}
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    try:
        os.chmod(path, 0o600)
        os.chmod(path.parent, 0o700)
    except OSError:
        pass


def server_command() -> tuple[str, list[str]]:
    found = shutil.which("tradingwiser-mcp")
    if found:
        return found, []
    return sys.executable, ["-m", "mcp_servers.tradingwiser"]


def server_block(secrets_file: Path) -> dict:
    command, args = server_command()
    block: dict = {"command": command, "env": {"TRADINGWISER_SECRETS_FILE": str(secrets_file)}}
    if args:
        block["args"] = args
    return block


def merge_mcp_json(path: Path, block: dict) -> None:
    data: dict = {}
    if path.exists() and path.stat().st_size:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            data = loaded
    servers = data.get("mcpServers")
    if not isinstance(servers, dict):
        servers = {}
    servers["tradingwiser"] = block
    data["mcpServers"] = servers
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _drop_toml_section(text: str, header: str) -> str:
    lines = text.splitlines()
    kept: list[str] = []
    skipping = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            skipping = stripped == header
        if not skipping:
            kept.append(line)
    return "\n".join(kept).strip()


def merge_codex_toml(path: Path, secrets_file: Path) -> None:
    command, args = server_command()
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    existing = _drop_toml_section(existing, "[mcp_servers.tradingwiser]")
    existing = _drop_toml_section(existing, "[mcp_servers.tradingwiser.env]")
    block = ["[mcp_servers.tradingwiser]", f"command = {json.dumps(command)}"]
    if args:
        block.append(f"args = {json.dumps(args)}")
    block.append("")
    block.append("[mcp_servers.tradingwiser.env]")
    block.append(f"TRADINGWISER_SECRETS_FILE = {json.dumps(str(secrets_file))}")
    path.parent.mkdir(parents=True, exist_ok=True)
    body = existing.rstrip()
    path.write_text((body + "\n\n" if body else "") + "\n".join(block) + "\n", encoding="utf-8")


def mcp_config_path(client: str, scope: str, target: Path) -> Path:
    home = Path.home()
    if client == "cursor":
        if scope == "user":
            return home / ".cursor" / "mcp.json"
        return target / ".cursor" / "mcp.json"
    if client == "claude-desktop":
        if sys.platform == "darwin":
            return home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
        if sys.platform == "win32":
            appdata = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
            return appdata / "Claude" / "claude_desktop_config.json"
        return home / ".config" / "Claude" / "claude_desktop_config.json"
    if client == "claude-code":
        if scope == "user":
            return home / ".claude.json"
        return target / ".mcp.json"
    if client == "codex":
        return home / ".codex" / "config.toml"
    raise SystemExit(f"Unknown client {client}. Choose: {', '.join(CLIENTS)}")


def register_mcp(client: str, scope: str, target: Path, secrets_file: Path) -> Path:
    path = mcp_config_path(client, scope, target)
    if client == "codex":
        merge_codex_toml(path, secrets_file)
    else:
        merge_mcp_json(path, server_block(secrets_file))
    return path


def install_agents(client: str, target: Path) -> list[Path]:
    if client not in AGENT_DIRS:
        raise SystemExit(f"Unknown client {client}. Choose: {', '.join(AGENT_DIRS)}")
    dest_dir = target / AGENT_DIRS[client]
    dest_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    bodies: list[str] = []
    for resource in sorted(files("agents").iterdir(), key=lambda item: item.name):
        if not resource.name.endswith(".mdc"):
            continue
        text = resource.read_text(encoding="utf-8")
        dest = dest_dir / resource.name
        dest.write_text(text, encoding="utf-8")
        written.append(dest)
        bodies.append(_agent_body(text))
    if client == "codex" and bodies:
        agents_md = target / "AGENTS.md"
        if not agents_md.exists():
            agents_md.write_text("\n\n".join(bodies).rstrip() + "\n", encoding="utf-8")
            written.append(agents_md)
    return written


def _agent_body(text: str) -> str:
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4 :].lstrip("\n")
    return text


def _ask(prompt: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    if value:
        return value
    return default or ""


def _choose(title: str, options: list[tuple[str, str]], default: str | None = None) -> str:
    print()
    print(title)
    for index, (_key, label) in enumerate(options, start=1):
        print(f"  {index}  {label}")
    by_index = {str(i): key for i, (key, _label) in enumerate(options, start=1)}
    by_key = {key: key for key, _label in options}
    default_index = None
    if default is not None:
        for index, (key, _label) in enumerate(options, start=1):
            if key == default:
                default_index = str(index)
                break
    while True:
        raw = _ask("Choice", default_index)
        if raw in by_index:
            return by_index[raw]
        if raw in by_key:
            return by_key[raw]
        print(f"Enter a number from 1 to {len(options)}.")


def _ask_api_base() -> str:
    while True:
        value = _ask("Trading Wiser API base URL")
        parsed = urlparse(value)
        if parsed.scheme in ("http", "https") and parsed.netloc:
            return value.rstrip("/")
        print("Enter an http or https URL, for example https://tradingwiser.example")


def _ask_password() -> str:
    while True:
        first = getpass.getpass("Password: ")
        if not first:
            print("Password cannot be empty.")
            continue
        second = getpass.getpass("Password again: ")
        if first != second:
            print("Those did not match. Try again.")
            continue
        return first


def _prompt_credentials(api_base: str | None, username: str | None, password: str | None) -> tuple[str, str, str]:
    base = api_base or _ask_api_base()
    user = username or _ask("Username")
    if not user:
        raise SystemExit("Username is required.")
    secret = password if password is not None else _ask_password()
    if not secret:
        raise SystemExit("Password is required.")
    parsed = urlparse(base)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise SystemExit("API base URL must be an http or https URL.")
    return base.rstrip("/"), user, secret


def _run_install(
    what: str,
    client: str,
    scope: str,
    target: Path,
    api_base: str | None,
    username: str | None,
    password: str | None,
    replace_secrets: bool,
) -> int:
    target = target.resolve()
    written_secrets: Path | None = None
    if what in ("mcp", "both"):
        destination = secrets_path()
        if destination.exists() and not replace_secrets:
            answer = ""
            if sys.stdin.isatty():
                answer = _ask(f"Secrets file already exists at {destination}. Replace it? [y/N]")
            if answer.lower() not in ("y", "yes"):
                print(f"Keeping the existing secrets file at {destination}")
            else:
                replace_secrets = True
        if replace_secrets or not destination.exists():
            base, user, secret = _prompt_credentials(api_base, username, password)
            write_secrets(destination, base, user, secret)
            written_secrets = destination
            print(f"Saved credentials to {destination}")
            print("The password is in that file only. It is not printed here.")
        config = register_mcp(client, scope, target, destination)
        print(f"Registered the tradingwiser MCP server in {config}")
        print("That config points at the secrets file. It does not contain the password.")
        print("Reload MCP servers in the client.")
    if what in ("agents", "both"):
        written = install_agents(client, target)
        if not written:
            print("No agent files found in the package.", file=sys.stderr)
            return 1
        print("Installed agents:")
        for path in written:
            print(f"  {path}")
        if client == "claude-desktop":
            print("Claude Desktop does not load those files on its own.")
            print("Paste the one you need into the Claude Project custom instructions.")
        if client == "codex" and not (target / "AGENTS.md") in written:
            print("Codex reads AGENTS.md. An AGENTS.md is already in this project, so it was left as-is.")
            print(f"The agent text is in {target / AGENT_DIRS['codex']}")
    if written_secrets is None and what == "agents":
        print("Agents are installed. Run this again and choose MCP when you want to connect Trading Wiser.")
    return 0


def _interactive(args: argparse.Namespace) -> int:
    print("Trading Wiser setup")
    print("Only an onboarded, approved user should continue.")
    what = args.what or _choose(
        "What should I install?",
        [("mcp", "MCP server"), ("agents", "Agents"), ("both", "MCP server and agents")],
        default="both",
    )
    client = args.client or _choose(
        "Which app are you setting up?",
        [
            ("cursor", "Cursor"),
            ("claude-desktop", "Claude Desktop"),
            ("claude-code", "Claude Code"),
            ("codex", "Codex"),
        ],
    )
    scope = args.scope
    if scope is None and client in ("cursor", "claude-code"):
        scope = _choose(
            "Where should this apply?",
            [("project", "This project only"), ("user", "All projects for this user")],
            default="project",
        )
    if scope is None:
        scope = "user"
    return _run_install(
        what,
        client,
        scope,
        Path(args.target),
        args.api_base,
        args.username,
        args.password,
        replace_secrets=bool(args.api_base or args.username or args.password),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ai-momentum-analyzer",
        description="Set up the Trading Wiser MCP server and agents. Run with no arguments for a guided setup.",
    )
    sub = parser.add_subparsers(dest="command")
    install = sub.add_parser("install", help="Install the MCP server, the agents, or both")
    install.add_argument("what", nargs="?", choices=["mcp", "agents", "both"])
    install.add_argument("--client", choices=CLIENTS)
    install.add_argument("--scope", choices=["project", "user"])
    install.add_argument("--target", default=".", help="Project directory for project-scoped install")
    install.add_argument("--api-base", help="Trading Wiser API base URL. You will be asked if omitted.")
    install.add_argument("--username", help="Trading Wiser username. You will be asked if omitted.")
    install.add_argument(
        "--password-stdin",
        action="store_true",
        help="Read the password from stdin instead of a hidden prompt.",
    )
    legacy = sub.add_parser("install-agents", help="Copy agents into a project")
    legacy.add_argument("--client", choices=("cursor", "claude", "claude-code"))
    legacy.add_argument("--target", default=".")

    args = parser.parse_args(argv)
    if args.command is None or args.command == "install":
        if args.command is None:
            args = install.parse_args([])
            args.password = None
            return _interactive(args)
        password = sys.stdin.readline().rstrip("\n") if args.password_stdin else None
        needs_secret = args.what in ("mcp", "both") and (args.api_base or args.username or not secrets_path().exists())
        if needs_secret and password is None and not sys.stdin.isatty():
            raise SystemExit(
                "Non-interactive MCP install needs --api-base, --username, and --password-stdin."
            )
        args.password = password
        if not args.what or not args.client:
            return _interactive(args)
        scope = args.scope or ("user" if args.client in ("claude-desktop", "codex") else "project")
        return _run_install(
            args.what,
            args.client,
            scope,
            Path(args.target),
            args.api_base,
            args.username,
            args.password,
            replace_secrets=bool(args.api_base or args.username or args.password),
        )
    if args.command == "install-agents":
        client = "claude-code" if args.client == "claude" else args.client
        written = install_agents(client, Path(args.target).resolve())
        for path in written:
            print(path)
        return 0 if written else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
