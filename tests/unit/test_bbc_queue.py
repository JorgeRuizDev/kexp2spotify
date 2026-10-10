from datetime import UTC, datetime

import pytest

from kexp2spotify.domain import ManagedPlaylist, SongQueueItem, SongRecord
from kexp2spotify.ports import DestinationItem, MutationResult
from kexp2spotify.spotify_playlists import queue_items_from_records, reconcile_queue


class FakeDestination:
    def __init__(self, existing: list[str] | None = None) -> None:
        self.items = [
            DestinationItem(uri=uri, position=index)
            for index, uri in enumerate(existing or [])
        ]
        self.prepended: list[str] = []
        self.removed: list[str] = []

    def read_playlist_items(self, playlist_id: str) -> list[DestinationItem]:
        return list(self.items)

    def append_items(self, playlist_id: str, track_uris: list[str]) -> MutationResult:
        return MutationResult(changed=bool(track_uris))

    def prepend_items(self, playlist_id: str, track_uris: list[str]) -> MutationResult:
        self.prepended.extend(track_uris)
        self.items = [
            DestinationItem(uri=uri, position=index)
            for index, uri in enumerate(reversed(track_uris))
        ] + [
            DestinationItem(uri=item.uri, position=len(track_uris) + index)
            for index, item in enumerate(self.items)
        ]
        return MutationResult(changed=bool(track_uris))

    def remove_items(self, playlist_id: str, items: list[DestinationItem]) -> MutationResult:
        self.removed.extend(item.uri for item in items)
        return MutationResult(changed=bool(items))


def _queue(track: str, uri: str | None, order: int) -> SongQueueItem:
    return SongQueueItem(
        show_id="bbc:bbc_radio_one",
        track_id=f"bbc:bbc_radio_one:{track}",
        destination_uri=uri,
        queued_at=datetime(2026, 10, 10, 10, tzinfo=UTC),
        source_order=order,
    )


def test_same_capture_time_uses_stable_rms_order() -> None:
    records = [
        SongRecord(
            track_id=f"bbc:bbc_radio_one:{order}", song=str(order), artist="Artist",
            captured_at=datetime(2026, 10, 10, 10, tzinfo=UTC),
            raw_json={"source_order": order},
        )
        for order in (0, 1, 2)
    ]
    queue = queue_items_from_records("bbc:bbc_radio_one", records, lambda record: record.song)
    ordered = sorted(queue, key=lambda item: item.source_order or 0)
    assert [item.destination_uri for item in ordered] == ["0", "1", "2"]
    destination = FakeDestination()
    reconcile_queue(destination, _playlist(), queue, 10)
    assert destination.items[0].uri == "0"
    assert destination.items[1].uri == "1"
    assert destination.items[2].uri == "2"


def test_duplicate_uris_keep_existing_occurrence_and_preserve_playlist_position() -> None:
    destination = FakeDestination(["keep", "older"])
    queue = [_queue("again", "keep", 0), _queue("new", "new", 1)]
    playlist, appended, removed, skipped = reconcile_queue(destination, _playlist(), queue, 10)
    assert destination.prepended == ["new"]
    assert playlist.track_uris == ["new", "keep", "older"]
    assert appended == 1
    assert removed == skipped == 0


def test_unresolved_items_are_skipped_and_positive_limit_removes_oldest_first() -> None:
    destination = FakeDestination(["oldest"])
    queue = [_queue("missing", None, 0), _queue("new", "new", 1)]
    playlist, appended, removed, skipped = reconcile_queue(destination, _playlist(), queue, 1)
    assert playlist.track_uris == ["new"]
    assert destination.removed == ["oldest"]
    assert appended == removed == skipped == 1


def test_queue_rejects_non_positive_playlist_limit() -> None:
    with pytest.raises(ValueError, match="playlist limit must be positive"):
        reconcile_queue(FakeDestination(), _playlist(), [], 0)


def _playlist() -> ManagedPlaylist:
    return ManagedPlaylist(
        show_id="bbc:bbc_radio_one", provider_playlist_id="playlist", name="BBC Radio 1"
    )
