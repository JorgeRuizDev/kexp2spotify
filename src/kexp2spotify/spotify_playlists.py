"""Provider-neutral playlist reconciliation rules."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .config import Settings
from .domain import (
    ImageState,
    ManagedPlaylist,
    Show,
    SongQueueItem,
    SongRecord,
    SynchronizationResult,
)
from .errors import ConfigurationError, SpotifyProviderError
from .ports import DestinationItem, PlaylistDestination, PlaylistIdStore
from .spotify_artwork import prepare_cover
from .spotify_metadata import DESCRIPTION_SUFFIX


def playlist_name(show_name: str) -> str:
    normalized = " ".join(show_name.split())
    if not normalized:
        raise ValueError("show name must not be empty")
    return f"KEXP - {normalized}"


def playlist_description(now: datetime, timezone_name: str) -> str:
    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ConfigurationError(f"invalid Spotify timezone: {timezone_name}") from exc
    local = now.astimezone(zone)
    return (
        f"Last updated at {local:%H:%M} on {local:%d-%m-%Y} "
        f"({timezone_name}){DESCRIPTION_SUFFIX}"
    )


def reconcile_queue(
    destination: PlaylistDestination,
    playlist: ManagedPlaylist,
    items: Sequence[SongQueueItem],
    limit: int,
) -> tuple[ManagedPlaylist, int, int, int]:
    if limit <= 0:
        raise ValueError("playlist limit must be positive")
    existing = list(destination.read_playlist_items(playlist.provider_playlist_id))
    existing_uris = {item.uri for item in existing}
    ordered = sorted(
        items,
        key=lambda item: (item.queued_at, item.source_id or "", item.track_id),
        reverse=True,
    )
    new_uris: list[str] = []
    skipped = 0
    for item in ordered:
        if (
            not item.destination_uri
            or item.destination_uri in existing_uris
            or item.destination_uri in new_uris
        ):
            if not item.destination_uri:
                skipped += 1
            continue
        new_uris.append(item.destination_uri)
    prepend = getattr(destination, "prepend_items", None)
    if callable(prepend):
        # Spotify inserts every item at position 0, so send oldest-to-newest
        # to preserve the desired newest-to-oldest order in the playlist.
        prepend(playlist.provider_playlist_id, list(reversed(new_uris)))
        combined = [
            DestinationItem(uri=uri, position=index) for index, uri in enumerate(new_uris)
        ] + [
            DestinationItem(uri=item.uri, position=len(new_uris) + index)
            for index, item in enumerate(existing)
        ]
    else:
        # Compatibility with simple destinations that only support appending.
        destination.append_items(playlist.provider_playlist_id, new_uris)
        combined = existing + [
            DestinationItem(uri=uri, position=len(existing) + index)
            for index, uri in enumerate(new_uris)
        ]
    remove_count = max(0, len(combined) - limit)
    removed = combined[-remove_count:] if remove_count else []
    if removed:
        destination.remove_items(playlist.provider_playlist_id, removed)
    kept_count = len(combined) - remove_count
    playlist.track_uris = [item.uri for item in combined[:kept_count]]
    return playlist, len(new_uris), len(removed), skipped


def reconcile_show(
    destination: PlaylistDestination,
    show: Show,
    items: Sequence[SongQueueItem],
    settings: Settings,
    now: datetime,
    image_bytes: bytes | None = None,
    playlist_store: PlaylistIdStore | None = None,
) -> SynchronizationResult:
    description = playlist_description(now, show.timezone or settings.spotify_timezone)
    name = playlist_name(show.name)
    stored_playlist_id = (
        playlist_store.get_playlist_id(show.id) if playlist_store is not None else None
    )
    playlist = (
        ManagedPlaylist(show_id=show.id, provider_playlist_id=stored_playlist_id, name=name)
        if stored_playlist_id
        else destination.find_managed_playlist(show.id, name)
    )
    created = 0
    if playlist is None:
        playlist = destination.create_playlist(show, name, description)
        created = 1
    if playlist_store is not None:
        playlist_store.save_playlist_id(show.id, playlist.provider_playlist_id)
    playlist, appended, removed, skipped = reconcile_queue(
        destination, playlist, items, settings.spotify_playlist_limit
    )
    destination.update_details(playlist.provider_playlist_id, name, description)
    image_state = apply_cover(destination, playlist.provider_playlist_id, image_bytes)
    return SynchronizationResult(
        shows=1,
        created_playlists=created,
        updated_playlists=1,
        appended_tracks=appended,
        removed_tracks=removed,
        skipped_tracks=skipped,
        artwork_updated=1 if image_state is ImageState.UPDATED else 0,
        artwork_preserved=1 if image_state is ImageState.PRESERVED else 0,
        artwork_unavailable=1 if image_state is ImageState.UNAVAILABLE else 0,
    )


def queue_items_from_records(
    show_id: str, records: Sequence[SongRecord], resolver: Callable[[SongRecord], str | None]
) -> list[SongQueueItem]:
    """Map source records into the provider-neutral queue boundary."""

    result: list[SongQueueItem] = []
    for record in records:
        queued_at = record.captured_at
        if isinstance(record.airdate, datetime):
            queued_at = record.airdate
        elif isinstance(record.airdate, str):
            try:
                parsed = datetime.fromisoformat(record.airdate.replace("Z", "+00:00"))
                if parsed.tzinfo is not None:
                    queued_at = parsed
            except ValueError:
                pass
        result.append(
            SongQueueItem(
                show_id=show_id,
                track_id=record.track_id,
                destination_uri=resolver(record),
                queued_at=queued_at,
                source_id=str(record.id) if record.id is not None else None,
            )
        )
    return result


def apply_cover(
    destination: PlaylistDestination, playlist_id: str, image_bytes: bytes | None
) -> ImageState:
    """Apply artwork without making an unavailable image fatal to queue sync."""

    if not image_bytes:
        return ImageState.UNAVAILABLE
    image_bytes = prepare_cover(image_bytes)
    if image_bytes is None:
        return ImageState.UNAVAILABLE
    try:
        result = destination.update_cover(playlist_id, image_bytes)
    except SpotifyProviderError:
        return ImageState.PRESERVED
    return ImageState.UPDATED if result.changed else ImageState.PRESERVED
