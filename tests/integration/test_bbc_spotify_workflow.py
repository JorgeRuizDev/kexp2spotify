from datetime import UTC, datetime
from pathlib import Path

from kexp2spotify.bbc_catalog import get_bbc_service
from kexp2spotify.bbc_sync import synchronize_bbc_services
from kexp2spotify.config import Settings
from kexp2spotify.domain import ManagedPlaylist, SongRecord
from kexp2spotify.ports import DestinationItem, MutationResult


class FakeSource:
    def __init__(self) -> None:
        self.records: dict[str, list[SongRecord]] = {}
        self.failed: set[str] = set()

    def fetch_latest_segments(self, request):
        if request.service_id in self.failed:
            raise RuntimeError("source unavailable")
        return list(self.records.get(request.service_id, []))


class FakeSpotify:
    def __init__(self) -> None:
        self.playlists: dict[str, ManagedPlaylist] = {}
        self.items: dict[str, list[DestinationItem]] = {}
        self.created: list[str] = []
        self.searches: list[str] = []

    def resolve_track(self, query: str) -> str | None:
        self.searches.append(query)
        return f"spotify:track:{query.rsplit(' ', 1)[-1]}"

    def find_managed_playlist(self, show_id: str, expected_name: str):
        return self.playlists.get(show_id)

    def create_playlist(self, show, name: str, description: str):
        self.created.append(name)
        playlist = ManagedPlaylist(
            show_id=show.id,
            provider_playlist_id=f"playlist-{show.id}",
            name=name,
            description=description,
        )
        self.playlists[show.id] = playlist
        self.items[playlist.provider_playlist_id] = []
        return playlist

    def read_playlist_items(self, playlist_id: str):
        return list(self.items[playlist_id])

    def prepend_items(self, playlist_id: str, track_uris: list[str]):
        existing = self.items[playlist_id]
        self.items[playlist_id] = [
            DestinationItem(uri=uri, position=index)
            for index, uri in enumerate(reversed(track_uris))
        ] + [
            DestinationItem(uri=item.uri, position=len(track_uris) + index)
            for index, item in enumerate(existing)
        ]
        return MutationResult(changed=bool(track_uris))

    def append_items(self, playlist_id: str, track_uris: list[str]):
        return MutationResult(changed=bool(track_uris))

    def remove_items(self, playlist_id: str, items: list[DestinationItem]):
        remove = {item.uri for item in items}
        self.items[playlist_id] = [
            item for item in self.items[playlist_id] if item.uri not in remove
        ]
        return MutationResult(changed=bool(items))

    def update_details(self, playlist_id: str, name: str, description: str):
        return MutationResult(changed=True)

    def update_cover(self, playlist_id: str, image_bytes: bytes):
        return MutationResult(changed=True)


class UnresolvableSpotify(FakeSpotify):
    def resolve_track(self, query: str) -> None:
        self.searches.append(query)
        return None


def _record(service_id: str, segment_id: str, song: str, order: int) -> SongRecord:
    return SongRecord(
        track_id=f"bbc:{service_id}:{segment_id}",
        song=song,
        artist="Artist",
        captured_at=datetime(2026, 10, 10, 10, tzinfo=UTC),
        raw_json={"bbc_service_id": service_id, "source_order": order},
    )


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        kexp_plays_url="https://example.com/plays",
        fetch_limit=10,
        deduplication_window=10,
        database_path=tmp_path / "db.sqlite",
        request_timeout_seconds=2,
        config_file=tmp_path / "config.yml",
        spotify_playlist_limit=3,
    )


def test_repeat_runs_reuse_one_station_playlist_and_deduplicate_tracks(tmp_path: Path) -> None:
    source = FakeSource()
    source.records["bbc_radio_one"] = [
        _record("bbc_radio_one", "new", "Song New", 0),
        _record("bbc_radio_one", "old", "Song Old", 1),
    ]
    spotify = FakeSpotify()
    settings = _settings(tmp_path)
    service = get_bbc_service("bbc_radio_one")
    assert service is not None

    first = synchronize_bbc_services(source, spotify, spotify, [service], settings)
    second = synchronize_bbc_services(source, spotify, spotify, [service], settings)

    assert first.created_playlists == 1
    assert second.created_playlists == 0
    assert spotify.created == ["BBC Radio 1"]
    items = spotify.items["playlist-bbc:bbc_radio_one"]
    assert [item.uri for item in items] == ["spotify:track:New", "spotify:track:Old"]
    assert len({item.uri for item in items}) == len(items)


def test_station_failure_does_not_stop_other_station_updates(tmp_path: Path) -> None:
    source = FakeSource()
    source.failed.add("bbc_radio_one")
    source.records["bbc_radio_two"] = [_record("bbc_radio_two", "two", "Song Two", 0)]
    spotify = FakeSpotify()
    services = [get_bbc_service("bbc_radio_one"), get_bbc_service("bbc_radio_two")]
    result = synchronize_bbc_services(
        source, spotify, spotify, [service for service in services if service], _settings(tmp_path)
    )
    assert result.successful is False
    assert any("bbc_radio_one" in failure for failure in result.failures)
    assert spotify.created == ["BBC Radio 2"]
    assert "playlist-bbc:bbc_radio_two" in spotify.items


def test_station_without_resolved_tracks_does_not_create_empty_playlist(
    tmp_path: Path,
) -> None:
    service = get_bbc_service("bbc_radio_one")
    assert service is not None
    source = FakeSource()
    source.records[service.service_id] = [
        _record(service.service_id, "unresolved", "Unknown Song", 0)
    ]
    spotify = UnresolvableSpotify()
    result = synchronize_bbc_services(source, spotify, spotify, [service], _settings(tmp_path))

    assert result.created_playlists == 0
    assert result.skipped_tracks == 1
    assert spotify.created == []
    assert spotify.playlists == {}
