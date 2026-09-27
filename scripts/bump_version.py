"""Bump the package, plugin, and MCP server versions. Prints the new version."""

from __future__ import annotations

import re
import sys
from pathlib import Path

VERSION_RE = re.compile(r'^version = "(\d+)\.(\d+)\.(\d+)"', re.MULTILINE)


def next_version(current: str, bump: str) -> str:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", current)
    if not match:
        raise SystemExit(f"Not a major.minor.patch version: {current}")
    major, minor, _patch = (int(part) for part in match.groups())
    if bump == "major":
        return f"{major + 1}.0.0"
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    raise SystemExit("bump must be major or minor")


def bump_file(path: Path, bump: str) -> str:
    text = path.read_text(encoding="utf-8")
    found = VERSION_RE.search(text)
    if not found:
        raise SystemExit(f"No version field in {path}")
    current = ".".join(found.groups())
    updated = next_version(current, bump)
    path.write_text(VERSION_RE.sub(f'version = "{updated}"', text, count=1), encoding="utf-8")
    for manifest in (
        path.parent / "plugin.json",
        path.parent / ".claude-plugin" / "plugin.json",
    ):
        if manifest.exists():
            manifest_text = manifest.read_text(encoding="utf-8")
            manifest_text, count = re.subn(
                r'("version"\s*:\s*")\d+\.\d+\.\d+("\s*,?)',
                rf'\g<1>{updated}\g<2>',
                manifest_text,
                count=1,
            )
            if count:
                manifest.write_text(manifest_text, encoding="utf-8")
    package_version = path.parent / "ai_momentum_analyzer" / "__init__.py"
    if package_version.exists():
        package_text = package_version.read_text(encoding="utf-8")
        package_text, count = re.subn(
            r'(__version__\s*=\s*")\d+\.\d+\.\d+("\s*)',
            rf'\g<1>{updated}\g<2>',
            package_text,
            count=1,
        )
        if count:
            package_version.write_text(package_text, encoding="utf-8")
    server_file = path.parent / "mcp_servers" / "tradingwiser" / "server.py"
    if server_file.exists():
        server_text = server_file.read_text(encoding="utf-8")
        server_text, count = re.subn(
            r'("serverInfo"\s*:\s*\{"name"\s*:\s*SERVER_NAME,\s*"version"\s*:\s*")\d+\.\d+\.\d+("\})',
            rf'\g<1>{updated}\g<2>',
            server_text,
            count=1,
        )
        if count:
            server_file.write_text(server_text, encoding="utf-8")
    return updated


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2 or args[0] not in ("major", "minor"):
        raise SystemExit("usage: bump_version.py major|minor path/to/pyproject.toml")
    print(bump_file(Path(args[1]), args[0]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
