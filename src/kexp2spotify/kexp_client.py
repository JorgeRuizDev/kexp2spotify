"""HTTP adapter for the KEXP plays collection."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import httpx

from .config import Settings
from .errors import SourceError


class KexpClient:
    """Fetch and validate KEXP collection responses."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def fetch_plays(self) -> Sequence[dict[str, object]]:
        try:
            response = httpx.get(
                str(self.settings.kexp_plays_url),
                params={"limit": self.settings.fetch_limit},
                timeout=self.settings.request_timeout_seconds,
            )
            if response.status_code < 200 or response.status_code >= 300:
                raise SourceError(f"KEXP returned HTTP {response.status_code}")
            payload: Any = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise SourceError(f"KEXP request failed: {type(exc).__name__}") from exc
        items: Any = payload.get("results") if isinstance(payload, Mapping) else payload
        if not isinstance(items, list):
            raise SourceError("KEXP response has an unsupported collection shape")
        return [item for item in items[: self.settings.fetch_limit] if isinstance(item, dict)]

    def fetch_show(self, show_id: str) -> Mapping[str, object]:
        """Fetch the KEXP show metadata referenced by a play."""

        base = str(self.settings.kexp_plays_url).split("/v2/plays")[0]
        try:
            response = httpx.get(
                f"{base}/v2/shows/{show_id}/", timeout=self.settings.request_timeout_seconds
            )
            response.raise_for_status()
            payload: Any = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise SourceError(f"KEXP show request failed: {type(exc).__name__}") from exc
        if not isinstance(payload, Mapping):
            raise SourceError(f"KEXP show {show_id} returned an invalid response")
        return payload

    def fetch_image(self, image_url: str) -> bytes | None:
        """Fetch optional show artwork; an unavailable image is non-fatal."""

        try:
            response = httpx.get(image_url, timeout=self.settings.request_timeout_seconds)
            if 200 <= response.status_code < 300:
                return response.content
        except httpx.HTTPError:
            pass
        return None
