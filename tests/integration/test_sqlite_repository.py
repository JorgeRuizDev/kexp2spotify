from datetime import datetime, timezone
from pathlib import Path

from kexp2spotify.domain import SongRecord
from kexp2spotify.sqlite_repository import SQLiteRepository


def test_repository_round_trip_and_unique_track_id(tmp_path: Path) -> None:
    repository = SQLiteRepository(tmp_path / "songs.sqlite")
    record = SongRecord(track_id="t1", song="Song", artist="Artist", captured_at=datetime.now(timezone.utc), raw_json={"x": 1}, play_type="trackplay")
    assert repository.insert_many([record, record]) == 1
    assert repository.count() == 1
    assert repository.recent_track_ids(10) == {"t1"}
    repository.close()
