from pathlib import Path

from kexp2spotify.crawler import collect
from kexp2spotify.sqlite_repository import SQLiteRepository


def test_duplicate_track_ids_in_one_batch_are_counted_once(tmp_path: Path) -> None:
    repository = SQLiteRepository(tmp_path / "songs.sqlite")
    item = {"track_id": "t1", "song": "Song", "artist": "Artist", "play_type": "trackplay"}
    source = type("Source", (), {"fetch_plays": lambda self: [item, dict(item)]})()
    summary = collect(source, repository, 10)
    assert summary.inserted == 1
    assert summary.duplicate == 1
    repository.close()
