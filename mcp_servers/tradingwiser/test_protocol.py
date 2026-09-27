"""MCP stdio handshake against a local stand-in API. No real credentials."""

import json
import os
import subprocess
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


class _Handler(BaseHTTPRequestHandler):
    calls = []

    def log_message(self, fmt, *args):
        return

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length).decode())

    def _send(self, code, payload):
        raw = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        body = self._read_json()
        self.calls.append(("POST", self.path))
        if self.path != "/api/v3/auth/login":
            self._send(404, {"detail": "not found"})
            return
        if body.get("username") == "tester" and body.get("password") == "tester-pass":
            self._send(200, {"access_token": "token-1", "refresh_token": "r"})
            return
        self._send(401, {"detail": "Invalid credentials"})

    def do_GET(self):
        self.calls.append(
            ("GET", self.path.split("?")[0], self.headers.get("Authorization"), self.path)
        )
        if self.headers.get("Authorization") != "Bearer token-1":
            self._send(401, {"detail": "missing token"})
            return
        path = self.path.split("?")[0]
        if path == "/api/v3/ticker/AAPL/scan":
            self._send(200, {"symbol": "AAPL", "setup_grade": "A", "conviction_score": 80})
            return
        if path == "/api/v3/dashboard/key-dates":
            self._send(200, {"upcoming": [{"event_name": "CPI"}], "realized": []})
            return
        if path == "/api/v3/ticker/NVDA/indicators":
            self._send(200, {"timeframe": "1D", "rsi": [55.4]})
            return
        self._send(404, {"detail": "not found"})


def _frame(obj):
    return json.dumps(obj).encode() + b"\n"


def _read(proc):
    line = proc.stdout.readline()
    return json.loads(line.decode())


class ProtocolTest(unittest.TestCase):
    def test_scan_logs_in_then_reads(self):
        _Handler.calls = []
        server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        env = os.environ.copy()
        env.update(
            {
                "TRADINGWISER_API_BASE": f"http://127.0.0.1:{port}",
                "TRADINGWISER_USERNAME": "tester",
                "TRADINGWISER_PASSWORD": "tester-pass",
                "PYTHONPATH": str(Path(__file__).resolve().parents[2]),
            }
        )
        proc = subprocess.Popen(
            [sys.executable, "-m", "mcp_servers.tradingwiser"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        try:
            proc.stdin.write(_frame({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}))
            proc.stdin.write(_frame({"jsonrpc": "2.0", "method": "notifications/initialized"}))
            proc.stdin.write(
                _frame(
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {"name": "get_scan", "arguments": {"symbol": "AAPL"}},
                    }
                )
            )
            proc.stdin.close()
            init = _read(proc)
            result = _read(proc)
            proc.wait(timeout=5)
        finally:
            proc.kill()
            server.shutdown()

        self.assertEqual(init["result"]["serverInfo"]["name"], "tradingwiser")
        self.assertFalse(result["result"]["isError"])
        body = json.loads(result["result"]["content"][0]["text"])
        self.assertEqual(body["setup_grade"], "A")
        self.assertEqual(_Handler.calls[0][:2], ("POST", "/api/v3/auth/login"))
        self.assertEqual(_Handler.calls[1][0], "GET")
        self.assertEqual(_Handler.calls[1][2], "Bearer token-1")

    def test_key_dates_logs_in_then_reads_without_a_symbol(self):
        _Handler.calls = []
        server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        env = os.environ.copy()
        env.update(
            {
                "TRADINGWISER_API_BASE": f"http://127.0.0.1:{port}",
                "TRADINGWISER_USERNAME": "tester",
                "TRADINGWISER_PASSWORD": "tester-pass",
                "PYTHONPATH": str(Path(__file__).resolve().parents[2]),
            }
        )
        proc = subprocess.Popen(
            [sys.executable, "-m", "mcp_servers.tradingwiser"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        try:
            proc.stdin.write(_frame({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}))
            proc.stdin.write(_frame({"jsonrpc": "2.0", "method": "notifications/initialized"}))
            proc.stdin.write(
                _frame(
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {"name": "get_key_dates", "arguments": {}},
                    }
                )
            )
            proc.stdin.close()
            _read(proc)
            result = _read(proc)
            proc.wait(timeout=5)
        finally:
            proc.kill()
            server.shutdown()

        self.assertFalse(result["result"]["isError"])
        body = json.loads(result["result"]["content"][0]["text"])
        self.assertEqual(body["upcoming"][0]["event_name"], "CPI")
        self.assertEqual(_Handler.calls[0][:2], ("POST", "/api/v3/auth/login"))
        self.assertEqual(_Handler.calls[1][1], "/api/v3/dashboard/key-dates")
        self.assertEqual(_Handler.calls[1][2], "Bearer token-1")

    def test_indicators_requests_daily_when_timeframe_is_omitted(self):
        self._assert_indicator_timeframe({}, "1D")

    def test_indicators_forwards_weekly_when_requested(self):
        self._assert_indicator_timeframe({"timeframe": "1W"}, "1W")

    def _assert_indicator_timeframe(self, arguments, expected):
        _Handler.calls = []
        server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        env = os.environ.copy()
        env.update(
            {
                "TRADINGWISER_API_BASE": f"http://127.0.0.1:{port}",
                "TRADINGWISER_USERNAME": "tester",
                "TRADINGWISER_PASSWORD": "tester-pass",
                "PYTHONPATH": str(Path(__file__).resolve().parents[2]),
            }
        )
        proc = subprocess.Popen(
            [sys.executable, "-m", "mcp_servers.tradingwiser"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        try:
            proc.stdin.write(_frame({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}))
            proc.stdin.write(_frame({"jsonrpc": "2.0", "method": "notifications/initialized"}))
            proc.stdin.write(
                _frame(
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {
                            "name": "get_indicators",
                            "arguments": {"symbol": "NVDA", **arguments},
                        },
                    }
                )
            )
            proc.stdin.close()
            _read(proc)
            result = _read(proc)
            proc.wait(timeout=5)
        finally:
            proc.kill()
            server.shutdown()

        self.assertFalse(result["result"]["isError"])
        query = parse_qs(urlparse(_Handler.calls[1][3]).query)
        self.assertEqual(query.get("timeframe"), [expected])


if __name__ == "__main__":
    unittest.main()
