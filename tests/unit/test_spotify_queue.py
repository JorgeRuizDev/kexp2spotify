from datetime import UTC, datetime

from kexp2spotify.domain import ManagedPlaylist, SongQueueItem
from kexp2spotify.ports import DestinationItem, MutationResult
from kexp2spotify.spotify_playlists import reconcile_queue


class FakeDestination:
    def __init__(self) -> None:
        self.items = [DestinationItem(uri="spotify:track:old", position=0)]
        self.appended: list[str] = []
        self.prepended: list[str] = []
        self.removed: list[str] = []

    def read_playlist_items(self, playlist_id: str) -> list[DestinationItem]:
        return self.items

    def append_items(self, playlist_id: str, track_uris: list[str]) -> MutationResult:
        self.appended.extend(track_uris)
        return MutationResult(changed=bool(track_uris))

    def prepend_items(self, playlist_id: str, track_uris: list[str]) -> MutationResult:
        for uri in track_uris:
            self.items.insert(0, DestinationItem(uri=uri, position=0))
        self.prepended.extend(track_uris)
        return MutationResult(changed=bool(track_uris))

    def remove_items(self, playlist_id: str, items: list[DestinationItem]) -> MutationResult:
        self.removed.extend(item.uri for item in items)
        return MutationResult(changed=bool(items))


def test_reconcile_prepends_latest_first_and_removes_oldest() -> None:
    destination = FakeDestination()
    playlist = ManagedPlaylist(show_id="show", provider_playlist_id="playlist", name="KEXP - Show")
    items = [
        SongQueueItem(
            show_id="show",
            track_id="new",
            destination_uri="spotify:track:new",
            queued_at=datetime(2026, 1, 2, tzinfo=UTC),
        ),
        SongQueueItem(
            show_id="show",
            track_id="middle",
            destination_uri="spotify:track:middle",
            queued_at=datetime(2026, 1, 1, tzinfo=UTC),
        ),
    ]
    updated, appended, removed, skipped = reconcile_queue(destination, playlist, items, 2)
    assert destination.prepended == ["spotify:track:middle", "spotify:track:new"]
    assert updated.track_uris == ["spotify:track:new", "spotify:track:middle"]
    assert appended == 2
    assert removed == 1
    assert destination.removed == ["spotify:track:old"]
    assert skipped == 0
