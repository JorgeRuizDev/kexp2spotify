from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from kexp2spotify.domain import SongRecord, map_trackplay


def test_song_record_requires_trackplay_and_non_empty_fields() -> None:
    record = SongRecord(
        track_id="t1",
        song="Song",
        artist="Artist",
        captured_at=datetime.now(UTC),
        raw_json={},
        play_type="trackplay",
    )
    assert record.track_id == "t1"
    with pytest.raises(ValidationError):
        SongRecord(
            track_id="",
            song="Song",
            artist="Artist",
            captured_at=datetime.now(UTC),
            raw_json={},
            play_type="trackplay",
        )


def test_map_trackplay_falls_back_to_recording_id_when_track_id_is_null() -> None:
    record = map_trackplay(
        {
            "id": 123,
            "track_id": None,
            "recording_id": "recording-uuid",
            "song": "Song",
            "artist": "Artist",
            "play_type": "trackplay",
        },
        datetime.now(UTC),
    )

    assert record.track_id == "kexp-recording:recording-uuid"
    assert record.id == 123


def test_map_trackplay_uses_play_id_when_catalog_ids_are_missing() -> None:
    record = map_trackplay(
        {
            "id": 123,
            "track_id": None,
            "recording_id": None,
            "song": "Song",
            "artist": "Artist",
            "play_type": "trackplay",
        },
        datetime.now(UTC),
    )

    assert record.track_id == "kexp-play:123"
