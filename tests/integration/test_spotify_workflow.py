from datetime import UTC, datetime
from importlib import resources
from pathlib import Path

import pytest

import kexp2spotify.spotify_sync as spotify_sync
from kexp2spotify.config import Settings
from kexp2spotify.domain import ManagedPlaylist, SongRecord
from kexp2spotify.ports import DestinationItem, MutationResult
from kexp2spotify.spotify_sync import synchronize_records


class FakeSource:
    def __init__(self, image_bytes: bytes | None = None) -> None:
        self.image_bytes = image_bytes or (
            resources.files("kexp2spotify")
            .joinpath("assets")
            .joinpath("kexp-logo-black-on-orange.jpg")
            .read_bytes()
        )
        self.image_requests: list[str] = []

    def fetch_show(self, show_id: str) -> dict[str, object]:
        return {"program_name": "Morning Show", "program_image_uri": "https://image.test/show.jpg"}

    def fetch_image(self, image_url: str) -> bytes | None:
        self.image_requests.append(image_url)
        return self.image_bytes


class FakeSpotify:
    def __init__(self) -> None:
        self.items: dict[str, list[DestinationItem]] = {}
        self.playlists: dict[str, ManagedPlaylist] = {}
        self.queries: list[str] = []
        self.covers: dict[str, bytes] = {}
        self.cover_uploads: list[str] = []

    def resolve_track(self, query: str) -> str:
        self.queries.append(query)
        return f"spotify:track:{len(self.queries)}"

    def find_managed_playlist(self, show_id: str, expected_name: str):
        return self.playlists.get(show_id)

    def create_playlist(self, show, name: str, description: str):
        playlist_id = f"playlist-{len(self.playlists) + 1}"
        playlist = ManagedPlaylist(show_id=show.id, provider_playlist_id=playlist_id,
                                   name=name, description=description)
        self.playlists[show.id] = playlist
        self.items[playlist_id] = []
        return playlist

    def read_playlist_items(self, playlist_id: str) -> list[DestinationItem]:
        return self.items[playlist_id]

    def append_items(self, playlist_id: str, track_uris: list[str]) -> MutationResult:
        items = self.items[playlist_id]
        items.extend(DestinationItem(uri=uri, position=len(items)) for uri in track_uris)
        return MutationResult(changed=bool(track_uris))

    def remove_items(self, playlist_id: str, items: list[DestinationItem]) -> MutationResult:
        self.items[playlist_id] = [
            item for item in self.items[playlist_id] if item not in items
        ]
        return MutationResult(changed=bool(items))

    def update_details(self, playlist_id: str, name: str, description: str) -> MutationResult:
        return MutationResult(changed=True)

    def update_cover(self, playlist_id: str, image_bytes: bytes) -> MutationResult:
        self.covers[playlist_id] = image_bytes
        self.cover_uploads.append(playlist_id)
        return MutationResult(changed=True)


def test_current_kexp_records_sync_show_and_latest_playlists(tmp_path: Path) -> None:
    settings = Settings(kexp_plays_url="https://api.kexp.org/v2/plays/", fetch_limit=10,
                        deduplication_window=10, database_path=tmp_path / "db.sqlite",
                        request_timeout_seconds=2, config_file=tmp_path / "config.yml",
                        spotify_playlist_limit=10)
    records = [
        SongRecord(track_id="t1", song="Song", artist="Artist", captured_at=datetime.now(UTC),
                   raw_json={"show": 68007}, play_type="trackplay"),
    ]
    spotify = FakeSpotify()
    source = FakeSource()
    result = synchronize_records(
        source,
        spotify,
        spotify,
        records,
        settings,
        datetime(2026, 10, 10, 12, tzinfo=UTC),
    )
    assert result.shows == 1
    assert result.created_playlists == 2
    assert result.updated_playlists == 2
    assert result.appended_tracks == 2
    assert result.artwork_updated == 2
    assert spotify.items["playlist-1"][0].uri == "spotify:track:1"
    assert spotify.items["playlist-2"][0].uri == "spotify:track:1"
    assert source.image_requests == ["https://image.test/show.jpg"]
    assert spotify.covers["playlist-2"].startswith(b"\xff\xd8\xff")

    # A later run refreshes the existing Latest Tracks cover too.
    second_result = synchronize_records(
        source,
        spotify,
        spotify,
        records,
        settings,
        datetime(2026, 10, 10, 13, tzinfo=UTC),
    )
    assert second_result.created_playlists == 0
    assert spotify.cover_uploads.count("playlist-2") == 2


def test_latest_tracks_cover_does_not_depend_on_remote_image_fetch(tmp_path: Path) -> None:
    settings = Settings(
        kexp_plays_url="https://api.kexp.org/v2/plays/",
        fetch_limit=10,
        deduplication_window=10,
        database_path=tmp_path / "db.sqlite",
        request_timeout_seconds=2,
        config_file=tmp_path / "config.yml",
        spotify_playlist_limit=10,
    )
    records = [
        SongRecord(
            track_id="t1",
            song="Song",
            artist="Artist",
            captured_at=datetime.now(UTC),
            raw_json={"show": 68007},
            play_type="trackplay",
        ),
    ]
    source = FakeSource()
    source.image_bytes = None
    spotify = FakeSpotify()

    result = synchronize_records(source, spotify, spotify, records, settings)

    assert result.artwork_updated == 1
    assert result.artwork_unavailable == 1
    assert source.image_requests == ["https://image.test/show.jpg"]
    assert spotify.covers["playlist-2"].startswith(b"\xff\xd8\xff")


def test_missing_latest_tracks_asset_does_not_stop_track_sync(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = Settings(
        kexp_plays_url="https://api.kexp.org/v2/plays/",
        fetch_limit=10,
        deduplication_window=10,
        database_path=tmp_path / "db.sqlite",
        request_timeout_seconds=2,
        config_file=tmp_path / "config.yml",
        spotify_playlist_limit=10,
    )
    records = [
        SongRecord(
            track_id="t1",
            song="Song",
            artist="Artist",
            captured_at=datetime.now(UTC),
            raw_json={"show": 68007},
            play_type="trackplay",
        ),
    ]
    source = FakeSource()
    spotify = FakeSpotify()
    monkeypatch.setattr(spotify_sync, "_latest_tracks_image", lambda: None)

    result = synchronize_records(source, spotify, spotify, records, settings)

    assert result.appended_tracks == 2
    assert result.artwork_updated == 1
    assert result.artwork_unavailable == 1
    assert spotify.items["playlist-2"][0].uri == "spotify:track:1"
