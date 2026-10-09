"""Application service connecting KEXP records to the Spotify destination."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Protocol

from .config import Settings
from .domain import Show, SongRecord, SynchronizationResult
from .errors import SourceError
from .ports import PlaylistDestination
from .spotify_playlists import queue_items_from_records, reconcile_show


class ShowMetadataSource(Protocol):
    def fetch_show(self, show_id: str) -> Mapping[str, object]: ...
    def fetch_image(self, image_url: str) -> bytes | None: ...


class TrackResolver(Protocol):
    def resolve_track(self, query: str) -> str | None: ...


def synchronize_records(source: ShowMetadataSource, destination: PlaylistDestination,
                        resolver: TrackResolver, records: Sequence[SongRecord],
                        settings: Settings, now: datetime | None = None) -> SynchronizationResult:
    """Synchronize the current KEXP batch, grouped by stable show identity."""

    grouped: dict[str, list[SongRecord]] = defaultdict(list)
    for record in records:
        show_value = record.raw_json.get("show")
        if show_value is not None:
            grouped[str(show_value)].append(record)
    result = SynchronizationResult()
    execution_time = now or datetime.now(UTC)
    for show_id, show_records in grouped.items():
        metadata = source.fetch_show(show_id)
        name = metadata.get("program_name") or metadata.get("name")
        if not isinstance(name, str) or not name.strip():
            raise SourceError(f"KEXP show {show_id} has no usable program name")
        image_url = metadata.get("program_image_uri") or metadata.get("image_uri")
        show = Show(id=show_id, name=name,
                    image_url=image_url if isinstance(image_url, str) else None)
        queue = queue_items_from_records(
            show_id, show_records,
            lambda record: resolver.resolve_track(f"{record.artist} {record.song}"),
        )
        image = source.fetch_image(show.image_url) if show.image_url else None
        current = reconcile_show(destination, show, queue, settings, execution_time, image)
        result = SynchronizationResult(
            shows=result.shows + current.shows,
            created_playlists=result.created_playlists + current.created_playlists,
            updated_playlists=result.updated_playlists + current.updated_playlists,
            appended_tracks=result.appended_tracks + current.appended_tracks,
            removed_tracks=result.removed_tracks + current.removed_tracks,
            skipped_tracks=result.skipped_tracks + current.skipped_tracks,
            artwork_updated=result.artwork_updated + current.artwork_updated,
            artwork_preserved=result.artwork_preserved + current.artwork_preserved,
            artwork_unavailable=result.artwork_unavailable + current.artwork_unavailable,
            failures=result.failures + current.failures,
        )
    return result
