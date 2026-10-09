"""Collection use case and deduplication rules."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime

from pydantic import ValidationError

from .domain import SongRecord, map_trackplay
from .ports import PlaySource, SongRepository


class CrawlSummary:
    """Counts emitted by one collection cycle."""

    def __init__(
        self,
        received: int,
        eligible: int,
        discarded: int,
        duplicate: int,
        inserted: int,
        records: list[SongRecord] | None = None,
    ) -> None:
        self.received, self.eligible, self.discarded = received, eligible, discarded
        self.duplicate, self.inserted = duplicate, inserted
        self.records = records or []

    def as_dict(self) -> dict[str, int]:
        return {
            "received": self.received,
            "eligible": self.eligible,
            "discarded": self.discarded,
            "duplicate": self.duplicate,
            "inserted": self.inserted,
        }


def collect(
    source: PlaySource, repository: SongRepository, deduplication_window: int
) -> CrawlSummary:
    """Fetch, validate, deduplicate, and persist one source response."""

    items = source.fetch_plays()
    recent = repository.recent_track_ids(deduplication_window)
    records = []
    eligible_records: list[SongRecord] = []
    seen: set[str] = set()
    discarded = 0
    duplicates = 0
    now = datetime.now(UTC)
    for item in items:
        if not isinstance(item, Mapping) or item.get("play_type") != "trackplay":
            discarded += 1
            continue
        try:
            record = map_trackplay(item, now)
        except (ValidationError, ValueError, TypeError):
            discarded += 1
            continue
        eligible_records.append(record)
        if record.track_id in recent or record.track_id in seen:
            duplicates += 1
            continue
        seen.add(record.track_id)
        records.append(record)
    inserted = repository.insert_many(records)
    return CrawlSummary(
        len(items),
        len(eligible_records) + discarded,
        discarded,
        duplicates + len(records) - inserted,
        inserted,
        eligible_records,
    )
