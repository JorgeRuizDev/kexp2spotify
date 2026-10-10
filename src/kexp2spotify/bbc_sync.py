"""BBC station collection and station-level Spotify playlist synchronization."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from importlib import resources
from typing import Protocol

from .bbc_catalog import BbcService
from .config import Settings
from .domain import Show, SongQueueItem, SongRecord, SynchronizationResult
from .ports import (
    BbcLatestSegmentsRequest,
    BbcLatestSegmentsSource,
    PlaylistDestination,
    PlaylistIdStore,
    SongRepository,
)
from .spotify_playlists import queue_items_from_records, reconcile_show

logger = logging.getLogger("kexp2spotify")


def _service_image(asset_name: str) -> bytes | None:
    try:
        return resources.files("kexp2spotify").joinpath("assets", asset_name).read_bytes()
    except OSError as exc:
        logger.warning("BBC station artwork unavailable error_type=%s", type(exc).__name__)
        return None


def _service_image_from_url(source: object, image_url: str) -> bytes | None:
    fetch_image = getattr(source, "fetch_image", None)
    if not callable(fetch_image):
        return None
    try:
        return fetch_image(image_url)
    except Exception as exc:
        logger.warning(
            "BBC station artwork fetch failed operation=fetch error_type=%s",
            type(exc).__name__,
        )
        return None


class BbcTrackResolver(Protocol):
    def resolve_track(self, query: str) -> str | None: ...


def synchronize_bbc_service(
    source: BbcLatestSegmentsSource,
    destination: PlaylistDestination,
    resolver: BbcTrackResolver,
    service: BbcService,
    settings: Settings,
    now: datetime | None = None,
    repository: SongRepository | None = None,
    playlist_store: PlaylistIdStore | None = None,
) -> SynchronizationResult:
    """Fetch, persist, resolve, and reconcile one independent BBC radio queue."""

    service_id = service.service_id
    show_id = f"bbc:{service_id}"
    records = list(source.fetch_latest_segments(BbcLatestSegmentsRequest(service_id)))
    if repository is not None:
        repository.insert_many(records)
    if not records:
        return SynchronizationResult()

    failures: list[str] = []

    def resolve(record: SongRecord) -> str | None:
        try:
            return resolver.resolve_track(f"{record.artist} {record.song}")
        except Exception as exc:
            failures.append(
                f"BBC station {service_id} track resolution failed ({type(exc).__name__})"
            )
            logger.warning(
                "BBC track resolution failed station=%s operation=resolve error_type=%s",
                service_id,
                type(exc).__name__,
            )
            return None

    queue: list[SongQueueItem] = queue_items_from_records(show_id, records, resolve)
    if not any(item.destination_uri for item in queue):
        result = SynchronizationResult(skipped_tracks=len(queue))
        result.failures.extend(failures)
        return result

    if service.logo_url:
        image_bytes = _service_image_from_url(source, service.logo_url)
    else:
        image_bytes = _service_image(service.logo_asset) if service.logo_asset else None

    show = Show(id=show_id, name=service.name)
    current = reconcile_show(
        destination,
        show,
        queue,
        settings,
        now or datetime.now(UTC),
        image_bytes,
        playlist_store,
        playlist_name_override=service.name,
    )
    if service.logo_asset and current.artwork_preserved:
        logger.warning(
            "BBC station artwork preserved station=%s operation=upload",
            service_id,
        )
    current.failures.extend(failures)
    return current


def synchronize_bbc_services(
    source: BbcLatestSegmentsSource,
    destination: PlaylistDestination,
    resolver: BbcTrackResolver,
    services: Sequence[BbcService],
    settings: Settings,
    now: datetime | None = None,
    repository: SongRepository | None = None,
    playlist_store: PlaylistIdStore | None = None,
) -> SynchronizationResult:
    """Synchronize services sequentially, retaining successes across failures."""

    total = SynchronizationResult()
    for service in services:
        try:
            current = synchronize_bbc_service(
                source,
                destination,
                resolver,
                service,
                settings,
                now,
                repository,
                playlist_store,
            )
        except Exception as exc:
            logger.error(
                "BBC station update failed station=%s operation=synchronize error_type=%s",
                service.service_id,
                type(exc).__name__,
            )
            current = SynchronizationResult(
                failures=[
                    f"BBC station {service.service_id} synchronization failed "
                    f"({type(exc).__name__})"
                ]
            )
        total = _combine(total, current)
    return total


def _combine(
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
