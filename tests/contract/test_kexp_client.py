import json
from pathlib import Path

import httpx
import pytest

from kexp2spotify.config import Settings
from kexp2spotify.errors import SourceError
from kexp2spotify.kexp_client import KexpClient


def test_client_fetches_configured_limit_and_results(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    settings = Settings(kexp_plays_url="https://example.com/plays", fetch_limit=1, deduplication_window=2,
                        database_path=tmp_path / "db", request_timeout_seconds=1, config_file=tmp_path / "c.yml")
    def fake_get(url: str, **kwargs: object) -> httpx.Response:
        assert kwargs["params"] == {"limit": 1}
        return httpx.Response(200, json=json.loads(Path("tests/contract/fixtures/kexp_plays.json").read_text()))
    monkeypatch.setattr(httpx, "get", fake_get)
    assert len(KexpClient(settings).fetch_plays()) == 1


def test_client_rejects_malformed_collection(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    settings = Settings(kexp_plays_url="https://example.com/plays", fetch_limit=1, deduplication_window=2,
                        database_path=tmp_path / "db", request_timeout_seconds=1, config_file=tmp_path / "c.yml")
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: httpx.Response(200, json={"wrong": []}))
    with pytest.raises(SourceError):
        KexpClient(settings).fetch_plays()
