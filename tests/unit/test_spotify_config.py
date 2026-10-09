from pathlib import Path

import pytest

from kexp2spotify.config import load_settings
from kexp2spotify.errors import ConfigurationError


def test_spotify_environment_overrides_are_loaded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = tmp_path / "config.yml"
    config.write_text(
        "kexp_plays_url: https://example.com/plays\n"
        "fetch_limit: 5\n"
        "deduplication_window: 10\n"
        "database_path: db.sqlite\n"
        "request_timeout_seconds: 2\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "client-id")
    monkeypatch.setenv("SPOTIFY_PLAYLIST_LIMIT", "7")
    settings = load_settings(config)
    assert settings.spotify_client_id == "client-id"
    assert settings.spotify_playlist_limit == 7


def test_spotify_redirect_must_use_loopback_callback(tmp_path: Path) -> None:
    config = tmp_path / "config.yml"
    config.write_text(
        "kexp_plays_url: https://example.com/plays\n"
        "fetch_limit: 5\n"
        "deduplication_window: 10\n"
        "database_path: db.sqlite\n"
        "request_timeout_seconds: 2\n"
        "spotify_redirect_uri: http://localhost:8765/callback\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigurationError):
        load_settings(config)


def test_current_directory_dotenv_is_loaded_without_overriding_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = tmp_path / "config.yml"
    config.write_text(
        "kexp_plays_url: https://example.com/plays\n"
        "fetch_limit: 5\n"
        "deduplication_window: 10\n"
        "database_path: db.sqlite\n"
        "request_timeout_seconds: 2\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "SPOTIFY_CLIENT_ID=from-dotenv\nSPOTIFY_PLAYLIST_LIMIT=12\n",
        encoding="utf-8",
    )
    settings = load_settings(config)
    assert settings.spotify_client_id == "from-dotenv"
    assert settings.spotify_playlist_limit == 12

    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "from-process")
    assert load_settings(config).spotify_client_id == "from-process"
