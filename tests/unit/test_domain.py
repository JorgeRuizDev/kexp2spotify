from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from kexp2spotify.domain import SongRecord


def test_song_record_requires_trackplay_and_non_empty_fields() -> None:
    record = SongRecord(track_id="t1", song="Song", artist="Artist", captured_at=datetime.now(timezone.utc), raw_json={}, play_type="trackplay")
    assert record.track_id == "t1"
    with pytest.raises(ValidationError):
        SongRecord(track_id="", song="Song", artist="Artist", captured_at=datetime.now(timezone.utc), raw_json={}, play_type="trackplay")
