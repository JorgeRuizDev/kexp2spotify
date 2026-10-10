from pathlib import Path

import httpx

from kexp2spotify.config import Settings
from kexp2spotify.spotify_client import SpotifyClient


class FakeHttp:
    def __init__(self, body: dict[str, object] | None = None) -> None:
        self.urls: list[str] = []
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
    assert "multiple managed playlists match show 68013" in caplog.text
