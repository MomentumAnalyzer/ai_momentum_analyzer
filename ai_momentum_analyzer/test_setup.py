"""Setup writes credentials only to the secrets file."""

import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

from ai_momentum_analyzer.cli import install_agents, merge_codex_toml, merge_mcp_json, server_block, write_secrets


class SetupTest(unittest.TestCase):
    def test_mcp_config_points_at_secrets_and_omits_the_password(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            secrets = root / "secrets.json"
            write_secrets(secrets, "https://tradingwiser.example", "user", "s3cret")
            config = root / "mcp.json"
            config.write_text(json.dumps({"mcpServers": {"other": {"command": "other"}}}), encoding="utf-8")
            merge_mcp_json(config, server_block(secrets))
            text = config.read_text(encoding="utf-8")
            data = json.loads(text)
            self.assertNotIn("s3cret", text)
            self.assertEqual(data["mcpServers"]["other"]["command"], "other")
            self.assertEqual(
                data["mcpServers"]["tradingwiser"]["env"]["TRADINGWISER_SECRETS_FILE"],
                str(secrets),
            )
            mode = stat.S_IMODE(secrets.stat().st_mode)
            if os.name == "posix":
                self.assertEqual(mode & 0o077, 0)

    def test_codex_config_points_at_secrets_and_omits_the_password(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            secrets = root / "secrets.json"
            write_secrets(secrets, "https://tradingwiser.example", "user", "s3cret")
            config = root / "config.toml"
            config.write_text('[mcp_servers.other]\ncommand = "other"\n', encoding="utf-8")
            merge_codex_toml(config, secrets)
            text = config.read_text(encoding="utf-8")
            self.assertNotIn("s3cret", text)
            self.assertIn('[mcp_servers.other]', text)
            self.assertIn(str(secrets), text)

    def test_install_agents_copies_rules(self):
        with tempfile.TemporaryDirectory() as directory:
            written = install_agents("cursor", Path(directory))
        names = {path.name for path in written}
        self.assertIn("daily-holdings-review.mdc", names)
        self.assertIn("tw-signal-critic.mdc", names)


if __name__ == "__main__":
    unittest.main()
