from datetime import UTC, datetime
from pathlib import Path

from kexp2spotify.config import Settings
from kexp2spotify.domain import SongRecord
from kexp2spotify.ports import DestinationItem, MutationResult
from kexp2spotify.spotify_sync import synchronize_records


class FakeSource:
    def fetch_show(self, show_id: str) -> dict[str, object]:
        return {"program_name": "Morning Show", "program_image_uri": "https://image.test/show.jpg"}

    def fetch_image(self, image_url: str) -> bytes | None:
        return b"\xff\xd8\xffimage"


class FakeSpotify:
    def __init__(self) -> None:
        self.items: list[DestinationItem] = []
        self.playlist_created = False
        self.queries: list[str] = []

    def resolve_track(self, query: str) -> str:
        self.queries.append(query)
        return f"spotify:track:{len(self.queries)}"

    def find_managed_playlist(self, show_id: str, expected_name: str):
        return None if not self.playlist_created else self.created

    def create_playlist(self, show, name: str, description: str):
        from kexp2spotify.domain import ManagedPlaylist

        self.playlist_created = True
        self.created = ManagedPlaylist(show_id=show.id, provider_playlist_id="playlist",
                                       name=name, description=description)
        return self.created

    def read_playlist_items(self, playlist_id: str) -> list[DestinationItem]:
        return self.items

    def append_items(self, playlist_id: str, track_uris: list[str]) -> MutationResult:
        self.items.extend(DestinationItem(uri=uri, position=len(self.items)) for uri in track_uris)
        return MutationResult(changed=bool(track_uris))

    def remove_items(self, playlist_id: str, items: list[DestinationItem]) -> MutationResult:
        self.items = [item for item in self.items if item not in items]
        return MutationResult(changed=bool(items))

    def update_details(self, playlist_id: str, name: str, description: str) -> MutationResult:
        return MutationResult(changed=True)

    def update_cover(self, playlist_id: str, image_bytes: bytes) -> MutationResult:
        return MutationResult(changed=True)


def test_current_kexp_records_are_synchronized_to_one_spotify_playlist(tmp_path: Path) -> None:
    settings = Settings(kexp_plays_url="https://api.kexp.org/v2/plays/", fetch_limit=10,
                        deduplication_window=10, database_path=tmp_path / "db.sqlite",
                        request_timeout_seconds=2, config_file=tmp_path / "config.yml",
                        spotify_playlist_limit=10)
    records = [
        SongRecord(track_id="t1", song="Song", artist="Artist", captured_at=datetime.now(UTC),
                   raw_json={"show": 68007}, play_type="trackplay"),
    ]
    spotify = FakeSpotify()
    result = synchronize_records(FakeSource(), spotify, spotify, records, settings,
                                  datetime(2026, 10, 10, 12, tzinfo=UTC))
    assert result.shows == 1
    assert result.created_playlists == 1
    assert result.appended_tracks == 1
    assert result.artwork_updated == 1
    assert spotify.items[0].uri == "spotify:track:1"
