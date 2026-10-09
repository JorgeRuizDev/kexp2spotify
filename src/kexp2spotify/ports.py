"""Typed ports used by the application core."""

from __future__ import annotations

from typing import Protocol, Sequence

from .domain import SongRecord


class PlaySource(Protocol):
    """Source of provider play objects."""

    def fetch_plays(self) -> Sequence[dict[str, object]]: ...


class SongRepository(Protocol):
    """Persistence operations required by the crawler."""

    def recent_track_ids(self, limit: int) -> set[str]: ...

    def insert_many(self, records: Sequence[SongRecord]) -> int: ...
