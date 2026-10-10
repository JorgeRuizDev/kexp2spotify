from dataclasses import replace
from datetime import UTC, datetime
from importlib import resources
from pathlib import Path

from kexp2spotify.bbc_catalog import get_bbc_service
from kexp2spotify.bbc_sync import synchronize_bbc_services
from kexp2spotify.config import Settings
from kexp2spotify.domain import ManagedPlaylist, SongRecord
from kexp2spotify.errors import SpotifyProviderError
from kexp2spotify.ports import DestinationItem, MutationResult


class FakeSource:
    def __init__(self, image: bytes | None) -> None:
        self.image = image
        self.records = [
            SongRecord(
                track_id="bbc:bbc_radio_one:one", song="Song", artist="Artist",
                captured_at=datetime(2026, 10, 10, 10, tzinfo=UTC),
                raw_json={"bbc_service_id": "bbc_radio_one", "source_order": 0},
            )
        ]

    def fetch_latest_segments(self, request):
        return self.records

    def fetch_image(self, image_url: str):
        return self.image


class FakeSpotify:
    def __init__(self, reject_cover: bool = False) -> None:
        self.playlists: dict[str, ManagedPlaylist] = {}
        self.details: list[tuple[str, str]] = []
        self.cover_calls = 0
        self.reject_cover = reject_cover

    def resolve_track(self, query: str):
        return "spotify:track:resolved"

    def find_managed_playlist(self, show_id: str, expected_name: str):
        return self.playlists.get(show_id)

    def create_playlist(self, show, name: str, description: str):
        playlist = ManagedPlaylist(
            show_id=show.id, provider_playlist_id="playlist", name=name, description=description
        )
        self.playlists[show.id] = playlist
        return playlist

    def read_playlist_items(self, playlist_id: str):
        return []

    def prepend_items(self, playlist_id: str, track_uris: list[str]):
        return MutationResult(changed=bool(track_uris))

    def append_items(self, playlist_id: str, track_uris: list[str]):
        return MutationResult(changed=bool(track_uris))

    def remove_items(self, playlist_id: str, items: list[DestinationItem]):
        return MutationResult(changed=bool(items))

    def update_details(self, playlist_id: str, name: str, description: str):
        self.details.append((name, description))
        return MutationResult(changed=True)

    def update_cover(self, playlist_id: str, image_bytes: bytes):
        self.cover_calls += 1
        if self.reject_cover:
            raise SpotifyProviderError("cover rejected")
        return MutationResult(changed=True)


def test_station_name_update_description_and_optional_cover(tmp_path: Path) -> None:
    settings = Settings(
        kexp_plays_url="https://example.com/plays", fetch_limit=10,
        deduplication_window=10, database_path=tmp_path / "db.sqlite",
        request_timeout_seconds=2, config_file=tmp_path / "config.yml",
        spotify_timezone="Europe/Madrid",
    )
    service = get_bbc_service("bbc_radio_one")
    assert service is not None
    service = replace(service, logo_url="https://www.bbc.co.uk/test-logo.jpg")
    now = datetime(2026, 10, 10, 10, 30, tzinfo=UTC)
    image = (
        resources.files("kexp2spotify")
        .joinpath("assets", "kexp-logo-black-on-orange.jpg")
        .read_bytes()
    )
    spotify = FakeSpotify()
    result = synchronize_bbc_services(FakeSource(image), spotify, spotify, [service], settings, now)
    assert result.created_playlists == 1
    assert spotify.details[0][0] == "BBC Radio 1"
    assert spotify.details[0][1].startswith(
        "Last updated at 12:30 on 10-10-2026 (Europe/Madrid) ·  "
        "github.com/JorgeRuizDev/kexp2spotify"
    )
    assert "\n" not in spotify.details[0][1]
    assert spotify.details[0][1].endswith("[kexp2spotify-bbc:bbc_radio_one]")
    assert spotify.cover_calls == 1
    assert result.artwork_updated == 1


def test_missing_or_rejected_artwork_does_not_block_track_sync(tmp_path: Path) -> None:
    settings = Settings(
        kexp_plays_url="https://example.com/plays", fetch_limit=10,
        deduplication_window=10, database_path=tmp_path / "db.sqlite",
        request_timeout_seconds=2, config_file=tmp_path / "config.yml",
    )
    service = get_bbc_service("bbc_radio_one")
    assert service is not None
    service = replace(service, logo_url="https://www.bbc.co.uk/test-logo.jpg")
    unavailable = FakeSpotify()
    missing_result = synchronize_bbc_services(
        FakeSource(None), unavailable, unavailable, [service], settings
    )
    rejected = FakeSpotify(reject_cover=True)
    image = (
        resources.files("kexp2spotify")
        .joinpath("assets", "kexp-logo-black-on-orange.jpg")
        .read_bytes()
    )
    rejected_result = synchronize_bbc_services(
        FakeSource(image), rejected, rejected, [service], settings
    )
    assert missing_result.appended_tracks == rejected_result.appended_tracks == 1
    assert missing_result.artwork_unavailable == 1
    assert rejected_result.artwork_preserved == 1
