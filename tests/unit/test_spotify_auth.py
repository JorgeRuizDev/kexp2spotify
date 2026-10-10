from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from kexp2spotify.config import Settings
from kexp2spotify.domain import AuthorizationState
from kexp2spotify.errors import SpotifyScopeError
from kexp2spotify.spotify_auth import SpotifyAuthenticator


class FakeTokenHttp:
    def request(self, *args: object, **kwargs: object) -> httpx.Response:
        return httpx.Response(200, json={"access_token": "access-token"})


class FakeTokenStore:
    def __init__(self, state: AuthorizationState) -> None:
        self.state = state
        self.saved: AuthorizationState | None = None

    def load(self) -> AuthorizationState:
        return self.state

    def save(self, state: AuthorizationState) -> None:
        self.saved = state


def test_refresh_uses_persisted_scopes_when_response_omits_scope(tmp_path: Path) -> None:
    settings = Settings(
        kexp_plays_url="https://example.com/plays",
        fetch_limit=1,
        deduplication_window=2,
        database_path=tmp_path / "db.sqlite",
        request_timeout_seconds=1,
        config_file=tmp_path / "config.yml",
        spotify_client_id="client-id",
        spotify_token_path=tmp_path / "token.json",
    )
    stored = AuthorizationState(
        client_id="client-id",
        refresh_token="refresh-token",
        scope={"playlist-read-private", "playlist-modify-public", "playlist-modify-private"},
        obtained_at=datetime.now(UTC),
    )
    authenticator = SpotifyAuthenticator(settings, http=FakeTokenHttp())  # type: ignore[arg-type]
    store = FakeTokenStore(stored)
    authenticator.store = store  # type: ignore[assignment]

    with pytest.raises(SpotifyScopeError, match="ugc-image-upload.*spotify-login"):
        authenticator.load_and_refresh()

    assert store.saved is None
