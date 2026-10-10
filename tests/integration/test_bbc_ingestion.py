from datetime import UTC, datetime
from pathlib import Path

from kexp2spotify.domain import SongRecord
from kexp2spotify.sqlite_repository import SQLiteRepository


def test_station_attributed_bbc_records_persist_without_changing_kexp(
    tmp_path: Path,
) -> None:
    repository = SQLiteRepository(tmp_path / "songs.sqlite")
    captured_at = datetime(2026, 10, 10, tzinfo=UTC)
    kexp = SongRecord(
        track_id="kexp-track", song="KEXP song", artist="KEXP artist",
        captured_at=captured_at, raw_json={"show": 10},
    )
    bbc = SongRecord(
        track_id="bbc:bbc_radio_one:p01", song="BBC song", artist="BBC artist",
        captured_at=captured_at,
        raw_json={"bbc_service_id": "bbc_radio_one", "source_order": 0},
    )
    assert repository.insert_many([kexp, bbc]) == 2
    assert repository.insert_many([bbc]) == 0
    rows = repository.all_rows()
    assert [row["track_id"] for row in rows] == ["kexp-track", "bbc:bbc_radio_one:p01"]
    assert rows[0]["raw_json"] == '{"show": 10}'
    repository.close()
