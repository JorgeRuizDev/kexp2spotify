from pathlib import Path

import pytest

from kexp2spotify.config import load_settings
from kexp2spotify.errors import ConfigurationError


def test_yaml_load_and_environment_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = tmp_path / "config.yml"
    config.write_text("kexp_plays_url: https://example.com/plays\nfetch_limit: 5\ndeduplication_window: 10\ndatabase_path: db.sqlite\nrequest_timeout_seconds: 2\n", encoding="utf-8")
    monkeypatch.setenv("KEXP2SPOTIFY_FETCH_LIMIT", "7")
    settings = load_settings(config)
    assert settings.fetch_limit == 7


def test_missing_yaml_fails(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError):
        load_settings(tmp_path / "missing.yml")
