from base64 import b64encode
from importlib import resources
from pathlib import Path

import httpx

from kexp2spotify.config import Settings
from kexp2spotify.spotify_artwork import prepare_cover
from kexp2spotify.spotify_client import SpotifyClient


class FakeHttp:
    def __init__(self, body: dict[str, object] | None = None) -> None:
        self.urls: list[str] = []
        self.calls: list[tuple[str, str, dict[str, object]]] = []
        self.body = body or {
            "items": [
                {
                    "item": {
                        "uri": "spotify:track:already-there",
                        "id": "already-there",
                    }
                }
            ],
            "next": None,
        }

    def request(self, method: str, url: str, **kwargs: object) -> httpx.Response:
        self.urls.append(url)
        self.calls.append((method, url, kwargs))
        return httpx.Response(
            200,
            json=self.body,
        )


def test_read_playlist_items_reads_current_spotify_item_shape(tmp_path: Path) -> None:
    settings = Settings(
        kexp_plays_url="https://example.com/plays",
        fetch_limit=1,
        deduplication_window=2,
        database_path=tmp_path / "db",
        request_timeout_seconds=1,
        config_file=tmp_path / "c.yml",
    )
    http = FakeHttp()
    client = SpotifyClient(settings, "token", http=http)  # type: ignore[arg-type]

    items = client.read_playlist_items("playlist")

    assert [item.uri for item in items] == ["spotify:track:already-there"]
    assert "fields=items(item(uri,id)),next" in http.urls[0]


def test_update_cover_sends_base64_jpeg_within_spotify_limit(tmp_path: Path) -> None:
    settings = Settings(
        kexp_plays_url="https://example.com/plays",
        fetch_limit=1,
        deduplication_window=2,
        database_path=tmp_path / "db",
        request_timeout_seconds=1,
        config_file=tmp_path / "c.yml",
    )
    png = (
        resources.files("kexp2spotify")
        .joinpath("assets")
        .joinpath("kexp-logo-black-on-orange.jpg")
        .read_bytes()
    )
    jpeg = prepare_cover(png)
    assert jpeg is not None
    http = FakeHttp()
    client = SpotifyClient(settings, "token", http=http)  # type: ignore[arg-type]

    result = client.update_cover("playlist", jpeg)

    method, url, kwargs = http.calls[0]
    assert result.changed
    assert method == "PUT"
    assert url.endswith("/playlists/playlist/images")
    assert kwargs["headers"] == {"Content-Type": "image/jpeg"}
    assert kwargs["content"] == b64encode(jpeg)


def test_update_cover_rejects_base64_payload_over_spotify_limit(tmp_path: Path) -> None:
    settings = Settings(
        kexp_plays_url="https://example.com/plays",
        fetch_limit=1,
        deduplication_window=2,
        database_path=tmp_path / "db",
        request_timeout_seconds=1,
        config_file=tmp_path / "c.yml",
    )
    http = FakeHttp()
    client = SpotifyClient(settings, "token", http=http)  # type: ignore[arg-type]

    result = client.update_cover("playlist", b"\xff\xd8\xff" + b"x" * 196_610)

    assert not result.changed
    assert http.calls == []


def test_find_managed_playlist_prefers_stable_show_identity(tmp_path: Path) -> None:
    from kexp2spotify.spotify_metadata import DESCRIPTION_SUFFIX, playlist_identity_marker

    settings = Settings(
        kexp_plays_url="https://example.com/plays",
        fetch_limit=1,
        deduplication_window=2,
        database_path=tmp_path / "db",
        request_timeout_seconds=1,
        config_file=tmp_path / "c.yml",
    )
    http = FakeHttp(
        {
            "items": [
                {
                    "id": "legacy",
                    "name": "KEXP - Morning Show",
                    "description": f"Last updated{DESCRIPTION_SUFFIX}",
                },
                {
                    "id": "other-show",
                    "name": "KEXP - Morning Show",
                    "description": f"{playlist_identity_marker('68012')}{DESCRIPTION_SUFFIX}",
                },
                {
                    "id": "target-show",
                    "name": "KEXP - Morning Show",
                    "description": f"{playlist_identity_marker('68013')}{DESCRIPTION_SUFFIX}",
                },
            ],
            "next": None,
        }
    )
    client = SpotifyClient(settings, "token", http=http)  # type: ignore[arg-type]

    playlist = client.find_managed_playlist("68013", "KEXP - Morning Show")

    assert playlist is not None
    assert playlist.provider_playlist_id == "target-show"


def test_find_managed_playlist_adopts_duplicate_legacy_name_deterministically(
    tmp_path: Path, caplog
) -> None:
    from kexp2spotify.spotify_metadata import DESCRIPTION_SUFFIX

    settings = Settings(
        kexp_plays_url="https://example.com/plays",
        fetch_limit=1,
        deduplication_window=2,
        database_path=tmp_path / "db",
        request_timeout_seconds=1,
        config_file=tmp_path / "c.yml",
    )
    http = FakeHttp(
        {
            "items": [
                {
                    "id": "playlist-b",
                    "name": "KEXP - Morning Show",
                    "description": f"Last updated{DESCRIPTION_SUFFIX}",
                },
                {
                    "id": "playlist-a",
                    "name": "KEXP - Morning Show",
                    "description": f"Last updated{DESCRIPTION_SUFFIX}",
                },
            ],
            "next": None,
        }
    )
    client = SpotifyClient(settings, "token", http=http)  # type: ignore[arg-type]

    playlist = client.find_managed_playlist("68013", "KEXP - Morning Show")

    assert playlist is not None
    assert playlist.provider_playlist_id == "playlist-a"
    assert "multiple playlists match show 68013" in caplog.text
