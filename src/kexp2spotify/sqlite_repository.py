"""SQLite adapter with transactional batch persistence."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from datetime import date, datetime
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
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_songs_captured_at "
            "ON songs(captured_at DESC, row_id DESC)"
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS execution_runs (
                run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_date TEXT NOT NULL,
                command TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT NOT NULL,
                status TEXT NOT NULL,
                attempts INTEGER NOT NULL,
                received INTEGER NOT NULL DEFAULT 0,
                inserted INTEGER NOT NULL DEFAULT 0,
                shows INTEGER NOT NULL DEFAULT 0,
                appended INTEGER NOT NULL DEFAULT 0,
                error TEXT
            )"""
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS notification_state (
                notification_date TEXT PRIMARY KEY,
                sent_at TEXT NOT NULL
            )"""
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS managed_playlists (
                show_id TEXT PRIMARY KEY,
                provider_playlist_id TEXT NOT NULL
            )"""
        )
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
                        (id, track_id, song, artist, album, release_date, captured_at,
                         raw_json, airdate, play_type)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(track_id) DO NOTHING""",
                        (record.id, record.track_id, record.song, record.artist, record.album,
                         str(record.release_date) if record.release_date is not None else None,
                         record.captured_at.isoformat(),
                         json.dumps(record.raw_json, ensure_ascii=False),
                         str(record.airdate) if record.airdate is not None else None,
                         record.play_type),
                    )
                    inserted += cursor.rowcount
                return inserted
        except (sqlite3.Error, TypeError, ValueError) as exc:
            raise PersistenceError(f"batch persistence failed: {exc}") from exc

    def get_playlist_id(self, show_id: str) -> str | None:
        try:
            row = self.connection.execute(
                "SELECT provider_playlist_id FROM managed_playlists WHERE show_id = ?",
                (show_id,),
            ).fetchone()
            return str(row[0]) if row is not None else None
        except sqlite3.Error as exc:
            raise PersistenceError(f"playlist ID lookup failed: {exc}") from exc

    def save_playlist_id(self, show_id: str, playlist_id: str) -> None:
        try:
            with self.connection:
                self.connection.execute(
                    """INSERT INTO managed_playlists (show_id, provider_playlist_id)
                    VALUES (?, ?)
                    ON CONFLICT(show_id) DO UPDATE SET
                        provider_playlist_id = excluded.provider_playlist_id""",
                    (show_id, playlist_id),
                )
        except sqlite3.Error as exc:
            raise PersistenceError(f"playlist ID persistence failed: {exc}") from exc

    def all_rows(self) -> list[sqlite3.Row]:
        self.connection.row_factory = sqlite3.Row
        return list(self.connection.execute("SELECT * FROM songs ORDER BY row_id"))

    def record_execution(
        self,
        run_date: date,
        command: str,
        started_at: datetime,
        finished_at: datetime,
        status: str,
        attempts: int,
        summary: dict[str, int | str] | None = None,
        error: str | None = None,
    ) -> None:
        values = summary or {}
        try:
            with self.connection:
                self.connection.execute(
                    """INSERT INTO execution_runs
                    (run_date, command, started_at, finished_at, status, attempts,
                     received, inserted, shows, appended, error)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        run_date.isoformat(),
                        command,
                        started_at.isoformat(),
                        finished_at.isoformat(),
                        status, attempts, int(values.get("received", 0)),
                        int(values.get("inserted", 0)), int(values.get("shows", 0)),
                        int(values.get("appended_tracks", 0)), error,
                    ),
                )
        except sqlite3.Error as exc:
            raise PersistenceError(f"execution history persistence failed: {exc}") from exc

    def daily_execution_summary(self, run_date: date) -> dict[str, int]:
        row = self.connection.execute(
            """SELECT COUNT(*), SUM(status = 'success'), SUM(status = 'failed'),
               COALESCE(SUM(received), 0), COALESCE(SUM(inserted), 0),
               COALESCE(SUM(shows), 0), COALESCE(SUM(appended), 0)
               FROM execution_runs WHERE run_date = ?""", (run_date.isoformat(),)
        ).fetchone()
        return {
            "runs": int(row[0] or 0), "successful": int(row[1] or 0), "failed": int(row[2] or 0),
            "received": int(row[3] or 0), "inserted": int(row[4] or 0),
            "shows": int(row[5] or 0), "appended": int(row[6] or 0),
        }

    def daily_summary_sent(self, run_date: date) -> bool:
        return self.connection.execute(
            "SELECT 1 FROM notification_state WHERE notification_date = ?", (run_date.isoformat(),)
        ).fetchone() is not None

    def mark_daily_summary_sent(self, run_date: date, sent_at: datetime) -> None:
        with self.connection:
            self.connection.execute(
                "INSERT OR IGNORE INTO notification_state(notification_date, sent_at) "
                "VALUES (?, ?)",
                (run_date.isoformat(), sent_at.isoformat()),
            )
