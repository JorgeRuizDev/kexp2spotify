"""BBC RMS latest-segment HTTP adapter and provider-payload normalization."""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

import httpx

from .bbc_catalog import get_bbc_service
from .config import Settings
from .domain import SongRecord
from .errors import NonRetryableSourceError, SourceError
from .ports import BbcLatestSegmentsRequest

RMS_API_URL = "https://rms.api.bbc.co.uk/v2/services"
RMS_MAX_PAGE_LIMIT = 10
logger = logging.getLogger("kexp2spotify")


class BbcClient:
    """Fetch and normalize recent music segments for an allowlisted station."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def fetch_latest_segments(
        self, request: BbcLatestSegmentsRequest
    ) -> Sequence[SongRecord]:
        if get_bbc_service(request.service_id) is None:
            raise SourceError(f"unsupported BBC service {request.service_id!r}")
        url = f"{RMS_API_URL}/{request.service_id}/segments/latest"
        request_limit = min(self.settings.fetch_limit, RMS_MAX_PAGE_LIMIT)
        try:
            response = httpx.get(
                url,
                params={
                    "experience": "domestic",
                    "offset": 0,
                    "limit": request_limit,
                },
                timeout=self.settings.request_timeout_seconds,
                headers={"User-Agent": "KEXP2Spotify/0.1 (BBC RMS metadata client)"},
            )
            if response.status_code < 200 or response.status_code >= 300:
                error_type = (
                    NonRetryableSourceError
                    if 400 <= response.status_code < 500
                    and response.status_code not in {408, 425, 429}
                    else SourceError
                )
                raise error_type(
                    f"BBC station {request.service_id} latest segments returned HTTP "
                    f"{response.status_code}"
                )
            payload: Any = response.json()
        except SourceError:
            raise
        except (httpx.HTTPError, ValueError) as exc:
            raise SourceError(
                f"BBC station {request.service_id} latest-segments request failed: "
                f"{type(exc).__name__}"
            ) from exc
        segments: Any = payload.get("data") if isinstance(payload, Mapping) else None
        if not isinstance(segments, list):
            raise SourceError(
                f"BBC station {request.service_id} returned an unsupported collection shape"
            )
        captured_at = datetime.now(UTC)
        records: list[SongRecord] = []
        for source_order, segment in enumerate(segments[:request_limit]):
            if not isinstance(segment, Mapping):
                logger.warning(
                    "BBC segment skipped station=%s operation=normalize reason=invalid_item "
                    "source_order=%d",
                    request.service_id,
                    source_order,
                )
                continue
            record = normalize_segment(
                segment, request.service_id, captured_at=captured_at, source_order=source_order
            )
            if record is None:
                logger.warning(
                    "BBC segment skipped station=%s operation=normalize "
                    "reason=ineligible_or_malformed source_order=%d",
                    request.service_id,
                    source_order,
                )
                continue
            records.append(record)
        return records

    def fetch_image(self, image_url: str) -> bytes | None:
        """Fetch optional station artwork; network and HTTP failures are non-fatal."""

        try:
            response = httpx.get(image_url, timeout=self.settings.request_timeout_seconds)
            if 200 <= response.status_code < 300:
                return response.content
        except httpx.HTTPError as exc:
            logger.warning(
                "BBC station artwork request failed operation=fetch error_type=%s",
                type(exc).__name__,
            )
        return None


def normalize_segment(
    segment: Mapping[str, Any],
    service_id: str,
    captured_at: datetime,
    source_order: int,
) -> SongRecord | None:
    """Map one eligible RMS music segment to a provider-neutral song record."""

    if get_bbc_service(service_id) is None or segment.get("segment_type") != "music":
        return None
    segment_id = segment.get("id")
    if segment_id is None or not str(segment_id).strip():
        segment_id = segment.get("urn")
    if segment_id is None or not str(segment_id).strip():
        return None
    titles = segment.get("titles")
    if not isinstance(titles, Mapping):
        return None
    artist = titles.get("primary")
    song = titles.get("secondary")
    if not isinstance(artist, str) or not artist.strip():
        return None
    if not isinstance(song, str) or not song.strip():
        return None
    try:
        raw_segment = dict(segment)
        raw_segment["bbc_service_id"] = service_id
        raw_segment["source_order"] = source_order
        airdate = _absolute_timestamp(segment.get("airdate"))
        return SongRecord(
            id=None,
            track_id=f"bbc:{service_id}:{str(segment_id).strip()}",
            song=song.strip(),
            artist=artist.strip(),
            album=_optional_text(segment.get("album") or titles.get("album")),
            captured_at=captured_at.astimezone(UTC),
            raw_json=raw_segment,
            airdate=airdate,
            play_type="trackplay",
        )
    except (TypeError, ValueError):
        return None


def _optional_text(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _absolute_timestamp(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else None
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None
