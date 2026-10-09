"""Typed ports used by the application core."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from .domain import AuthorizationState, ManagedPlaylist, Show, SongRecord


class PlaySource(Protocol):
    """Source of provider play objects."""

    def fetch_plays(self) -> Sequence[dict[str, object]]: ...


class SongRepository(Protocol):
    """Persistence operations required by the crawler."""

    def recent_track_ids(self, limit: int) -> set[str]: ...

    def insert_many(self, records: Sequence[SongRecord]) -> int: ...


class TokenStore(Protocol):
    def load(self) -> AuthorizationState: ...
    def save(self, state: AuthorizationState) -> None: ...


class AuthorizationPort(Protocol):
    def authorize_interactive(self) -> AuthorizationState: ...
    def load_and_refresh(self) -> AuthorizationState: ...


@dataclass(frozen=True)
class DestinationItem:
    uri: str
    position: int
    item_id: str | None = None


@dataclass(frozen=True)
class MutationResult:
    changed: bool
    snapshot_id: str | None = None


class PlaylistDestination(Protocol):
    def find_managed_playlist(self, show_id: str, expected_name: str) -> ManagedPlaylist | None: ...
    def create_playlist(self, show: Show, name: str, description: str) -> ManagedPlaylist: ...
    def read_playlist_items(self, playlist_id: str) -> Sequence[DestinationItem]: ...
    def append_items(self, playlist_id: str, track_uris: Sequence[str]) -> MutationResult: ...
    def prepend_items(self, playlist_id: str, track_uris: Sequence[str]) -> MutationResult: ...
    def remove_items(
        self, playlist_id: str, items: Sequence[DestinationItem]
    ) -> MutationResult: ...
    def update_details(self, playlist_id: str, name: str, description: str) -> MutationResult: ...
    def update_cover(self, playlist_id: str, image_bytes: bytes) -> MutationResult: ...
