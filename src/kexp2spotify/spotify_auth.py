"""Spotify Authorization Code with PKCE and refresh support."""

from __future__ import annotations

import base64
import hashlib
import secrets
import urllib.parse
import webbrowser
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from typing import Any

from .config import Settings
from .domain import AuthorizationState
from .errors import (
    ConfigurationError,
    SpotifyAuthenticationError,
    SpotifyReauthorizationRequired,
    SpotifyScopeError,
)
from .spotify_http import SpotifyHttp
from .spotify_token_store import FileTokenStore

AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
REQUIRED_SCOPES = {
    "playlist-read-private",
    "playlist-modify-public",
    "playlist-modify-private",
    "ugc-image-upload",
}


def generate_pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    )
    return verifier, challenge


def authorization_url(settings: Settings, state: str, challenge: str) -> str:
    if not settings.spotify_client_id or not settings.spotify_redirect_uri:
        raise ConfigurationError("Spotify Client ID and redirect URI are required")
    query = urllib.parse.urlencode(
        {
            "client_id": settings.spotify_client_id,
            "response_type": "code",
            "redirect_uri": settings.spotify_redirect_uri,
            "scope": settings.spotify_scope,
            "state": state,
            "code_challenge_method": "S256",
            "code_challenge": challenge,
        }
    )
    return f"{AUTH_URL}?{query}"


class SpotifyAuthenticator:
    def __init__(self, settings: Settings, http: SpotifyHttp | None = None) -> None:
        self.settings = settings
        if not settings.spotify_token_path:
            raise ConfigurationError("spotify_token_path is required for Spotify authorization")
        self.store = FileTokenStore(settings.spotify_token_path)
        self.http = http or SpotifyHttp(settings.request_timeout_seconds)
        self.last_access_token: str | None = None

    def authorize_interactive(
        self, *, open_browser: bool = True, timeout: float = 300.0
    ) -> AuthorizationState:
        if not self.settings.spotify_client_id or not self.settings.spotify_redirect_uri:
            raise ConfigurationError("Spotify Client ID and redirect URI are required")
        verifier, challenge = generate_pkce()
        state = secrets.token_urlsafe(32)
        parsed = urllib.parse.urlparse(self.settings.spotify_redirect_uri)
        port = parsed.port
        if port is None:
            raise ConfigurationError("Spotify redirect URI must include a callback port")
        callback: dict[str, str] = {}

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                callback["code"] = query.get("code", [""])[0]
                callback["state"] = query.get("state", [""])[0]
                callback["error"] = query.get("error", [""])[0]
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Spotify authorization received. You may close this window.")

            def log_message(self, format: str, *args: Any) -> None:
                return

        server = HTTPServer(("127.0.0.1", port), Handler)
        thread = Thread(target=server.handle_request, daemon=True)
        thread.start()
        url = authorization_url(self.settings, state, challenge)
        print(f"Open this Spotify authorization URL:\n{url}")
        if open_browser:
            webbrowser.open(url)
        thread.join(timeout)
        server.server_close()
        if callback.get("state") != state:
            raise SpotifyAuthenticationError("Spotify callback state validation failed")
        if callback.get("error"):
            raise SpotifyAuthenticationError(f"Spotify authorization failed: {callback['error']}")
        if not callback.get("code"):
            raise SpotifyAuthenticationError(
                "Spotify callback did not contain an authorization code"
            )
        state_model = self._exchange_code(callback["code"], verifier)
        self.store.save(state_model)
        return state_model

    def _exchange_code(self, code: str, verifier: str) -> AuthorizationState:
        response = self.http.request(
            "POST",
            TOKEN_URL,
            data={
                "client_id": self.settings.spotify_client_id or "",
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.settings.spotify_redirect_uri or "",
                "code_verifier": verifier,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        payload = response.json()
        self.last_access_token = str(payload.get("access_token", "")) or None
        return self._state_from_payload(payload, None)

    def load_and_refresh(self) -> AuthorizationState:
        current = self.store.load()
        if not current.refresh_token:
            raise SpotifyReauthorizationRequired("Spotify reauthorization is required")
        response = self.http.request(
            "POST",
            TOKEN_URL,
            data={
                "client_id": self.settings.spotify_client_id or current.client_id,
                "grant_type": "refresh_token",
                "refresh_token": current.refresh_token,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        payload = response.json()
        self.last_access_token = str(payload.get("access_token", "")) or None
        return self._state_from_payload(payload, current)

    def _state_from_payload(
        self, payload: Any, previous: AuthorizationState | None
    ) -> AuthorizationState:
        if not isinstance(payload, dict) or not payload.get("refresh_token") and previous is None:
            raise SpotifyAuthenticationError(
                "Spotify token response did not contain a refresh token"
            )
        if "scope" in payload:
            scope = set(str(payload["scope"]).split())
        elif previous is not None:
            scope = set(previous.scope)
        else:
            scope = set(self.settings.spotify_scope.split())
        missing = REQUIRED_SCOPES - scope
        if missing:
            raise SpotifyScopeError(
                "Spotify authorization is missing required scopes: "
                f"{sorted(missing)}; run spotify-login to reauthorize"
            )
        state = AuthorizationState(
            client_id=self.settings.spotify_client_id or (previous.client_id if previous else ""),
            refresh_token=str(
                payload.get("refresh_token", previous.refresh_token if previous else "")
            ),
            scope=scope,
            obtained_at=previous.obtained_at if previous else datetime.now(UTC),
            last_refresh_at=datetime.now(UTC),
            status="valid",
        )
        self.store.save(state)
        return state
