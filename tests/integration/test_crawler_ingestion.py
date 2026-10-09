from pathlib import Path

from kexp2spotify.crawler import collect
from kexp2spotify.sqlite_repository import SQLiteRepository


class FakeSource:
    def fetch_plays(self) -> list[dict[str, object]]:
        return [
            {"id": 1, "track_id": "t1", "song": "Song", "artist": "Artist", "play_type": "trackplay", "extra": "kept"},
            {"id": 2, "track_id": "ignored", "song": "News", "artist": "DJ", "play_type": "airbreak"},
        ]


def test_collect_persists_only_valid_trackplays_and_is_idempotent(tmp_path: Path) -> None:
    repository = SQLiteRepository(tmp_path / "songs.sqlite")
    first = collect(FakeSource(), repository, 100)
    second = collect(FakeSource(), repository, 100)
    assert first.inserted == 1
    assert second.inserted == 0
    assert repository.count() == 1
    repository.close()
