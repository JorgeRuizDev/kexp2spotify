from datetime import UTC, datetime
from pathlib import Path

import pytest

from kexp2spotify.domain import AuthorizationState
from kexp2spotify.errors import SpotifyAuthenticationError
from kexp2spotify.spotify_token_store import FileTokenStore


def test_token_store_round_trip_and_replacement(tmp_path: Path) -> None:
    path = tmp_path / "spotify-token.json"
    store = FileTokenStore(path)
    first = AuthorizationState(
        client_id="client", refresh_token="old", obtained_at=datetime.now(UTC)
    )
    second = first.model_copy(update={"refresh_token": "new"})
    store.save(first)
    assert store.load().refresh_token == "old"
    store.save(second)
    assert store.load().refresh_token == "new"
    assert "new" in path.read_text(encoding="utf-8")


def test_token_store_reports_missing_and_corrupt_files(tmp_path: Path) -> None:
    store = FileTokenStore(tmp_path / "missing.json")
    with pytest.raises(SpotifyAuthenticationError):
        store.load()
    store.path.write_text("not json", encoding="utf-8")
    with pytest.raises(SpotifyAuthenticationError):
        store.load()
