"""Interactive setup for the Trading Wiser MCP server and portable skills.

The password is written only to a secrets file outside the project. MCP client
configs store the path to that file, not the password.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import runpy
import shutil
import sys
import zipfile
from importlib.metadata import PackageNotFoundError, version
from importlib.resources import as_file, files
from pathlib import Path
from urllib.parse import urlparse

CLIENTS = ("cursor", "claude-desktop", "claude-code", "codex")
SKILL_DIRS = {
    "cursor": Path(".agents") / "skills",
    "claude-code": Path(".claude") / "skills",
    "codex": Path(".agents") / "skills",
}
SKILL_NAMES = ("daily-holdings-review", "tw-signal-critic", "zone-analysis-report")
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


def render_report_main() -> int:
    """Run the report renderer bundled with the installed package."""
    renderer = files("skills").joinpath(
        "zone-analysis-report", "scripts", "render_report.py"
    )
    with as_file(renderer) as renderer_path:
        module = runpy.run_path(str(renderer_path), run_name="tradingwiser_report_renderer")
        return module["main"](sys.argv[1:])


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


def install_skills(client: str, target: Path, scope: str = "project") -> list[Path]:
    """Install portable skills at the directory each supported client discovers."""
    target = target.resolve()
    if client == "claude-desktop":
        zip_dir = target / "tradingwiser-claude-skills"
        zip_dir.mkdir(parents=True, exist_ok=True)
        written: list[Path] = []
        for skill_name in SKILL_NAMES:
            resource = files("skills").joinpath(skill_name)
            archive = zip_dir / f"{skill_name}.zip"
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
                _zip_resource(bundle, resource, Path(skill_name))
            written.append(archive)
        plugin_archive = zip_dir / "trading-wiser-claude-plugin.zip"
        try:
            plugin_version = version("ai-momentum-analyzer")
        except PackageNotFoundError:
            plugin_version = "0.0.0"
        manifest = {
            "name": "trading-wiser",
            "description": "Trading Wiser workflow skills. Configure MCP separately with ai-momentum-analyzer.",
            "version": plugin_version,
            "author": {"name": "Trading Wiser"},
        }
        with zipfile.ZipFile(plugin_archive, "w", zipfile.ZIP_DEFLATED) as bundle:
            bundle.writestr(".claude-plugin/plugin.json", json.dumps(manifest, indent=2) + "\n")
            for skill_name in SKILL_NAMES:
                _zip_resource(bundle, files("skills").joinpath(skill_name), Path("skills") / skill_name)
        written.append(plugin_archive)
        return written
    if client not in SKILL_DIRS:
        raise SystemExit(f"Unknown client {client}. Choose: {', '.join(CLIENTS)}")
    base = Path.home() if scope == "user" else target
    dest_dir = base / SKILL_DIRS[client]
    dest_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for skill_name in SKILL_NAMES:
        resource = files("skills").joinpath(skill_name)
        destination = dest_dir / skill_name
        _copy_resource(resource, destination)
        written.append(destination / "SKILL.md")
    return written


def _copy_resource(resource, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for child in resource.iterdir():
        target = destination / child.name
        if child.is_dir():
            _copy_resource(child, target)
        else:
            target.write_bytes(child.read_bytes())


def _zip_resource(bundle: zipfile.ZipFile, resource, prefix: Path) -> None:
    for child in resource.iterdir():
        target = prefix / child.name
        if child.is_dir():
            _zip_resource(bundle, child, target)
        else:
            bundle.writestr(target.as_posix(), child.read_bytes())


# Kept as a source-compatible alias for existing internal callers.
install_agents = install_skills


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
    if what in ("skills", "agents", "both"):
        written = install_skills(client, target, scope)
        if not written:
            print("No skill files found in the package.", file=sys.stderr)
            return 1
        print("Installed skills:")
        for path in written:
            print(f"  {path}")
        if client == "claude-desktop":
            print("Upload the plugin ZIP in Claude → Customize → Plugins → Add → Upload a custom plugin.")
            print("Or upload individual skill ZIPs in Claude → Customize → Skills → + Create skill → Upload a skill.")
        elif scope == "user":
            print("Installed for this user account.")
        else:
            print("Installed for this project. Restart or reload the client if a skill does not appear.")
    if written_secrets is None and what == "agents":
        print("The legacy 'agents' choice is supported as an alias for 'skills'.")
    if written_secrets is None and what in ("skills", "agents"):
        print("Skills are installed. Run this again and choose MCP when you want to connect Trading Wiser.")
    return 0


def _interactive(args: argparse.Namespace) -> int:
    print("Trading Wiser setup")
    print("Only an onboarded, approved user should continue.")
    what = args.what or _choose(
        "What should I install?",
        [("mcp", "MCP server"), ("skills", "Skills"), ("both", "MCP server and skills")],
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
    if scope is None and client in ("cursor", "claude-code", "codex"):
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
        description="Set up the Trading Wiser MCP server and skills. Run with no arguments for a guided setup.",
    )
    sub = parser.add_subparsers(dest="command")
    install = sub.add_parser("install", help="Install the MCP server, skills, or both")
    install.add_argument("what", nargs="?", choices=["mcp", "skills", "agents", "both"])
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
    legacy = sub.add_parser("install-agents", help="Legacy alias: copy portable skills into a project")
    legacy.add_argument("--client", choices=("cursor", "claude", "claude-code", "codex"))
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
        scope = args.scope or ("user" if args.client == "claude-desktop" else "project")
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
        written = install_skills(client, Path(args.target).resolve())
        for path in written:
            print(path)
        return 0 if written else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
