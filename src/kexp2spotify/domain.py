"""Provider-independent domain models and rules."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any

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
        return value.astimezone(UTC)


def map_trackplay(item: Mapping[str, Any], captured_at: datetime) -> SongRecord:
    """Map a provider object while retaining the complete original object."""

    track_id = item.get("track_id")
    if track_id is None or not str(track_id).strip():
        recording_id = item.get("recording_id")
        play_id = item.get("id")
        if recording_id is not None and str(recording_id).strip():
            track_id = f"kexp-recording:{recording_id}"
        elif play_id is not None and str(play_id).strip():
            track_id = f"kexp-play:{play_id}"
        else:
            track_id = ""

    return SongRecord(
        id=item.get("id"),
        track_id=str(track_id),
        song=item.get("song", ""),
        artist=item.get("artist", ""),
        album=item.get("album"),
        release_date=item.get("release_date"),
        airdate=item.get("airdate"),
        captured_at=captured_at,
        raw_json=dict(item),
        play_type=item.get("play_type", ""),
    )


class ImageState(StrEnum):
    UPDATED = "updated"
    PRESERVED = "preserved"
    UNAVAILABLE = "unavailable"


class Show(BaseModel):
    """Stable source show identity used by destination adapters."""

    model_config = ConfigDict(extra="forbid")
    id: str
    name: str
    image_url: str | None = None
    timezone: str | None = None

    @field_validator("id", "name")
    @classmethod
    def required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("show values must not be empty")
        return value


class SongQueueItem(BaseModel):
    """One source song ordered by its queue timestamp."""

    model_config = ConfigDict(extra="forbid")
    show_id: str
    track_id: str
    destination_uri: str | None = None
    queued_at: datetime
    source_id: str | None = None
    source_order: int | None = None

    @field_validator("show_id", "track_id")
    @classmethod
    def queue_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("queue identity must not be empty")
        return value

    @field_validator("queued_at")
    @classmethod
    def queue_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("queued_at must be timezone-aware")
        return value


class ManagedPlaylist(BaseModel):
    model_config = ConfigDict(extra="forbid")
    show_id: str
    provider_playlist_id: str
    name: str
    description: str = ""
    track_uris: list[str] = Field(default_factory=list, max_length=10000)
    image_state: ImageState = ImageState.UNAVAILABLE

    @field_validator("show_id", "provider_playlist_id", "name")
    @classmethod
    def playlist_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("playlist identity must not be empty")
        return value

    @field_validator("track_uris")
    @classmethod
    def unique_tracks(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("playlist tracks must be unique")
        return value


class AuthorizationState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    client_id: str
    refresh_token: str
    scope: set[str] = Field(default_factory=set)
    obtained_at: datetime
    last_refresh_at: datetime | None = None
    status: str = "valid"

    @field_validator("client_id", "refresh_token")
    @classmethod
    def authorization_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("authorization values must not be empty")
        return value


class SynchronizationResult(BaseModel):
    shows: int = 0
    created_playlists: int = 0
    updated_playlists: int = 0
    appended_tracks: int = 0
    removed_tracks: int = 0
    skipped_tracks: int = 0
    artwork_updated: int = 0
    artwork_preserved: int = 0
    artwork_unavailable: int = 0
    failures: list[str] = Field(default_factory=list)
    reauthorization_required: bool = False

    @property
    def successful(self) -> bool:
        return not self.failures and not self.reauthorization_required
