"""SQLite adapter with transactional batch persistence."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from pathlib import Path

from .domain import SongRecord
from .errors import PersistenceError


class SQLiteRepository:
    """Persist song records in a local SQLite database."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.connection = sqlite3.connect(self.path)
            self.connection.execute("PRAGMA foreign_keys = ON")
            self._initialize()
        except sqlite3.Error as exc:
            raise PersistenceError(f"database initialization failed: {exc}") from exc

    def _initialize(self) -> None:
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS songs (
                row_id INTEGER PRIMARY KEY AUTOINCREMENT,
                id INTEGER,
                track_id TEXT NOT NULL UNIQUE,
                song TEXT NOT NULL,
                artist TEXT NOT NULL,
                album TEXT,
                release_date TEXT,
                captured_at TEXT NOT NULL,
                raw_json TEXT NOT NULL,
                airdate TEXT,
                play_type TEXT NOT NULL
            )"""
        )
        self.connection.execute("CREATE INDEX IF NOT EXISTS idx_songs_captured_at ON songs(captured_at DESC, row_id DESC)")
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def count(self) -> int:
        return int(self.connection.execute("SELECT COUNT(*) FROM songs").fetchone()[0])

    def recent_track_ids(self, limit: int) -> set[str]:
        rows = self.connection.execute(
            "SELECT track_id FROM songs ORDER BY captured_at DESC, row_id DESC LIMIT ?", (limit,)
        ).fetchall()
        return {str(row[0]) for row in rows}

    def insert_many(self, records: Sequence[SongRecord]) -> int:
        if not records:
            return 0
        try:
            with self.connection:
                inserted = 0
                for record in records:
                    cursor = self.connection.execute(
                        """INSERT INTO songs
                        (id, track_id, song, artist, album, release_date, captured_at, raw_json, airdate, play_type)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(track_id) DO NOTHING""",
                        (record.id, record.track_id, record.song, record.artist, record.album,
                         str(record.release_date) if record.release_date is not None else None,
                         record.captured_at.isoformat(), json.dumps(record.raw_json, ensure_ascii=False),
                         str(record.airdate) if record.airdate is not None else None, record.play_type),
                    )
                    inserted += cursor.rowcount
                return inserted
        except (sqlite3.Error, TypeError, ValueError) as exc:
            raise PersistenceError(f"batch persistence failed: {exc}") from exc

    def all_rows(self) -> list[sqlite3.Row]:
        self.connection.row_factory = sqlite3.Row
        return list(self.connection.execute("SELECT * FROM songs ORDER BY row_id"))
