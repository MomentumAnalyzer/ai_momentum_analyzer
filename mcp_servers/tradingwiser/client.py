"""HTTP client for the Trading Wiser API.

Opens a connection only after username and password are present and login
succeeds. Data routes are never called without a bearer token from that login.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener


class AuthError(RuntimeError):
    """Credentials missing or rejected. No data route was called."""


class _SameHostRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        original = urlparse(req.full_url)
        target = urlparse(newurl)
        if target.scheme not in ("http", "https") or target.netloc != original.netloc:
            raise AuthError("Refusing redirect off the Trading Wiser host")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class TradingWiserClient:
    def __init__(self, base_url: str, username: str, password: str):
        host = urlparse(base_url)
        if host.scheme not in ("http", "https") or not host.netloc:
            raise AuthError("TRADINGWISER_API_BASE must be an http(s) URL")
        if not username or not password:
            raise AuthError("Trading Wiser username and password are required")
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self._access: str | None = None
        self._opener = build_opener(_SameHostRedirect)

    @classmethod
    def from_env(cls) -> "TradingWiserClient":
        secrets_file = os.environ.get("TRADINGWISER_SECRETS_FILE", "").strip()
        if secrets_file:
            return cls.from_secrets_file(secrets_file)
        base = os.environ.get("TRADINGWISER_API_BASE", "").strip()
        username = os.environ.get("TRADINGWISER_USERNAME", "").strip()
        password = os.environ.get("TRADINGWISER_PASSWORD", "").strip()
        if not base or not username or not password:
            raise AuthError(
                "Set TRADINGWISER_SECRETS_FILE, or set TRADINGWISER_API_BASE, "
                "TRADINGWISER_USERNAME, and TRADINGWISER_PASSWORD"
            )
        return cls(base, username, password)

    @classmethod
    def from_secrets_file(cls, path: str) -> "TradingWiserClient":
        file = Path(path)
        try:
            raw = file.read_text(encoding="utf-8")
        except OSError as exc:
            raise AuthError(f"Cannot read secrets file: {path}") from exc
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise AuthError(f"Secrets file is not valid JSON: {path}") from exc
        if not isinstance(data, dict):
            raise AuthError("Secrets file must be a JSON object")
        base = str(data.get("api_base", "")).strip()
        username = str(data.get("username", "")).strip()
        password = str(data.get("password", "")).strip()
        if not base or not username or not password:
            raise AuthError("Secrets file must include api_base, username, and password")
        return cls(base, username, password)

    def login(self) -> None:
        body = self._request(
            "POST",
            "/api/v3/auth/login",
            {"username": self.username, "password": self.password},
            auth=False,
        )
        token = body.get("access_token")
        if not token:
            raise AuthError("Trading Wiser login did not return a token")
        self._access = token

    def get_json(self, path: str, query: dict | None = None) -> dict:
        if self._access is None:
            self.login()
        try:
            return self._request("GET", path, query=query, auth=True)
        except AuthError:
            self._access = None
            self.login()
            return self._request("GET", path, query=query, auth=True)

    def _request(
        self,
        method: str,
        path: str,
        payload: dict | None = None,
        query: dict | None = None,
        auth: bool = True,
    ) -> dict:
        url = self.base_url + path
        if query:
            clean = {k: v for k, v in query.items() if v is not None}
            if clean:
                url = url + "?" + urlencode(clean)
        data = None
        headers = {
            "Accept": "application/json",
            "ngrok-skip-browser-warning": "true",
        }
        if payload is not None:
            data = json.dumps(payload).encode()
            headers["Content-Type"] = "application/json"
        if auth:
            if not self._access:
                raise AuthError("Not logged in")
            headers["Authorization"] = f"Bearer {self._access}"
        request = Request(url, data=data, headers=headers, method=method)
        try:
            with self._opener.open(request, timeout=30) as response:
                raw = response.read().decode()
        except HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            if exc.code in (401, 403):
                raise AuthError(f"Trading Wiser rejected the session ({exc.code})") from exc
            raise AuthError(f"Trading Wiser request failed ({exc.code}): {detail}") from exc
        except URLError as exc:
            raise AuthError(f"Trading Wiser connection failed: {exc.reason}") from exc
        if not raw:
            return {}
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
        return {"data": parsed}
