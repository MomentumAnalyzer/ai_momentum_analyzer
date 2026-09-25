"""Bump the version in pyproject.toml. Prints the new version."""

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
    path.write_text(
        VERSION_RE.sub(f'version = "{updated}"', text, count=1),
        encoding="utf-8",
    )
    return updated


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2 or args[0] not in ("major", "minor"):
        raise SystemExit("usage: bump_version.py major|minor path/to/pyproject.toml")
    print(bump_file(Path(args[1]), args[0]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
