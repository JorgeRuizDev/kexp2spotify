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
            response = httpx.get(str(self.settings.kexp_plays_url), params={"limit": self.settings.fetch_limit},
                                timeout=self.settings.request_timeout_seconds)
            if response.status_code < 200 or response.status_code >= 300:
                raise SourceError(f"KEXP returned HTTP {response.status_code}")
            payload: Any = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise SourceError(f"KEXP request failed: {type(exc).__name__}") from exc
        items: Any = payload.get("results") if isinstance(payload, Mapping) else payload
        if not isinstance(items, list):
            raise SourceError("KEXP response has an unsupported collection shape")
        return [item for item in items[: self.settings.fetch_limit] if isinstance(item, dict)]
