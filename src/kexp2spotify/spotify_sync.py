"""Application service connecting KEXP records to the Spotify destination."""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from importlib import resources
from typing import Protocol

from .config import Settings
from .domain import Show, SongQueueItem, SongRecord, SynchronizationResult
from .errors import SourceError
from .ports import PlaylistDestination, PlaylistIdStore
from .spotify_playlists import queue_items_from_records, reconcile_show


class ShowMetadataSource(Protocol):
    def fetch_show(self, show_id: str) -> Mapping[str, object]: ...
    def fetch_image(self, image_url: str) -> bytes | None: ...


class TrackResolver(Protocol):
    def resolve_track(self, query: str) -> str | None: ...


LATEST_TRACKS_ID = "kexp-latest-tracks"
LATEST_TRACKS_NAME = "Latest Tracks"
LATEST_TRACKS_IMAGE_PATH = ("assets", "kexp-logo-black-on-orange.jpg")
logger = logging.getLogger("kexp2spotify")


def _latest_tracks_image() -> bytes | None:
    try:
        return (
            resources.files("kexp2spotify")
            .joinpath(*LATEST_TRACKS_IMAGE_PATH)
            .read_bytes()
        )
    except OSError as exc:
        logger.warning("latest tracks cover unavailable error_type=%s", type(exc).__name__)
        return None


def synchronize_records(
    source: ShowMetadataSource,
    destination: PlaylistDestination,
    resolver: TrackResolver,
    records: Sequence[SongRecord],
    settings: Settings,
    now: datetime | None = None,
    playlist_store: PlaylistIdStore | None = None,
) -> SynchronizationResult:
    """Synchronize the current KEXP batch, grouped by stable show identity."""

    grouped: dict[str, list[SongRecord]] = defaultdict(list)
    for record in records:
        show_value = record.raw_json.get("show")
        if show_value is not None:
            grouped[str(show_value)].append(record)
    result = SynchronizationResult()
    latest_items: list[SongQueueItem] = []
    execution_time = now or datetime.now(UTC)
    for show_id, show_records in grouped.items():
        metadata = source.fetch_show(show_id)
        name = metadata.get("program_name") or metadata.get("name")
        if not isinstance(name, str) or not name.strip():
            raise SourceError(f"KEXP show {show_id} has no usable program name")
        image_url = metadata.get("program_image_uri") or metadata.get("image_uri")
        show = Show(
            id=show_id,
            name=name,
            image_url=image_url if isinstance(image_url, str) else None,
        )
        queue = queue_items_from_records(
            show_id, show_records,
            lambda record: resolver.resolve_track(f"{record.artist} {record.song}"),
        )
        latest_items.extend(
            item.model_copy(update={"show_id": LATEST_TRACKS_ID}) for item in queue
        )
        image = source.fetch_image(show.image_url) if show.image_url else None
        current = reconcile_show(
            destination,
            show,
            queue,
            settings,
            execution_time,
            image,
            playlist_store,
        )
        result = _combine_results(result, current)
    if latest_items:
        latest_tracks = Show(id=LATEST_TRACKS_ID, name=LATEST_TRACKS_NAME)
        image = _latest_tracks_image()
        current = reconcile_show(
            destination,
            latest_tracks,
            latest_items,
            settings,
            execution_time,
            image,
            playlist_store,
        )
        result = _combine_results(result, current.model_copy(update={"shows": 0}))
    return result


def _combine_results(
    total: SynchronizationResult, current: SynchronizationResult
) -> SynchronizationResult:
    return SynchronizationResult(
        shows=total.shows + current.shows,
        created_playlists=total.created_playlists + current.created_playlists,
        updated_playlists=total.updated_playlists + current.updated_playlists,
        appended_tracks=total.appended_tracks + current.appended_tracks,
        removed_tracks=total.removed_tracks + current.removed_tracks,
        skipped_tracks=total.skipped_tracks + current.skipped_tracks,
        artwork_updated=total.artwork_updated + current.artwork_updated,
        artwork_preserved=total.artwork_preserved + current.artwork_preserved,
        artwork_unavailable=total.artwork_unavailable + current.artwork_unavailable,
        failures=total.failures + current.failures,
    )
