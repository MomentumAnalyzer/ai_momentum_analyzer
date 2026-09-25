"""The client must not open a connection without Trading Wiser credentials."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mcp_servers.tradingwiser.client import AuthError, TradingWiserClient


class ClientGateTest(unittest.TestCase):
    def test_missing_env_does_not_call_the_network(self):
        with patch.dict("os.environ", {}, clear=True):
            with patch("mcp_servers.tradingwiser.client.build_opener") as opener:
                with self.assertRaises(AuthError):
                    TradingWiserClient.from_env()
                opener.assert_not_called()

    def test_blank_password_does_not_build_a_client(self):
        with self.assertRaises(AuthError):
            TradingWiserClient("https://tradingwiser.example", "user", "")

    def test_secrets_file_is_used_when_set(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "secrets.json"
            path.write_text(
                json.dumps(
                    {
                        "api_base": "https://tradingwiser.example",
                        "username": "user",
                        "password": "secret",
                    }
                ),
                encoding="utf-8",
            )
            with patch.dict("os.environ", {"TRADINGWISER_SECRETS_FILE": str(path)}, clear=True):
                client = TradingWiserClient.from_env()
        self.assertEqual(client.base_url, "https://tradingwiser.example")
        self.assertEqual(client.username, "user")
        self.assertEqual(client.password, "secret")

    def test_incomplete_secrets_file_does_not_call_the_network(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "secrets.json"
            path.write_text(json.dumps({"api_base": "https://tradingwiser.example"}), encoding="utf-8")
            with patch.dict("os.environ", {"TRADINGWISER_SECRETS_FILE": str(path)}, clear=True):
                with patch("mcp_servers.tradingwiser.client.build_opener") as opener:
                    with self.assertRaises(AuthError):
                        TradingWiserClient.from_env()
                    opener.assert_not_called()


if __name__ == "__main__":
    unittest.main()
