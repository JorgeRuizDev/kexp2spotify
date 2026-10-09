from pathlib import Path

import httpx

from kexp2spotify.config import Settings
from kexp2spotify.spotify_client import SpotifyClient


class FakeHttp:
    def __init__(self) -> None:
        self.urls: list[str] = []

    def request(self, method: str, url: str, **kwargs: object) -> httpx.Response:
        self.urls.append(url)
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "item": {
                            "uri": "spotify:track:already-there",
                            "id": "already-there",
                        }
                    }
                ],
                "next": None,
            },
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
