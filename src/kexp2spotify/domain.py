"""Provider-independent domain models and rules."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SongRecord(BaseModel):
    """A validated trackplay ready for persistence."""

    model_config = ConfigDict(extra="forbid")
    id: int | None = None
    track_id: str
    song: str
    artist: str
    album: str | None = None
    release_date: date | str | None = None
    captured_at: datetime
    raw_json: dict[str, Any]
    airdate: datetime | str | None = None
    play_type: str = "trackplay"

    @field_validator("track_id", "song", "artist")
    @classmethod
    def non_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be empty")
        return value

    @field_validator("play_type")
    @classmethod
    def trackplay_only(cls, value: str) -> str:
        if value != "trackplay":
            raise ValueError("play_type must be trackplay")
        return value

    @field_validator("captured_at")
    @classmethod
    def utc_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("captured_at must be timezone-aware")
        return value.astimezone(timezone.utc)


def map_trackplay(item: Mapping[str, Any], captured_at: datetime) -> SongRecord:
    """Map a provider object while retaining the complete original object."""

    return SongRecord(
        id=item.get("id"),
        track_id=item.get("track_id", ""),
        song=item.get("song", ""),
        artist=item.get("artist", ""),
        album=item.get("album"),
        release_date=item.get("release_date"),
        airdate=item.get("airdate"),
        captured_at=captured_at,
        raw_json=dict(item),
        play_type=item.get("play_type", ""),
    )
