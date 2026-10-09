"""Typed HTTP transport for Spotify APIs."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

from .errors import (
    SpotifyAuthenticationError,
    SpotifyProviderError,
    SpotifyRateLimitError,
    SpotifyReauthorizationRequired,
)
from .logging import redact


class SpotifyHttp:
    def __init__(self, timeout: float = 10.0, transport: httpx.BaseTransport | None = None) -> None:
        self._client = httpx.Client(timeout=timeout, transport=transport)

    def close(self) -> None:
        self._client.close()

    def request(
        self,
        method: str,
        url: str,
        *,
        token: str | None = None,
        json: Mapping[str, Any] | None = None,
        data: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        content: bytes | None = None,
        params: Mapping[str, str | int] | None = None,
    ) -> httpx.Response:
        request_headers = dict(headers or {})
        if token:
            request_headers["Authorization"] = f"Bearer {token}"
        try:
            response = self._client.request(
                method,
                url,
                headers=request_headers,
                json=json,
                data=data,
                content=content,
                params=params,
            )
        except httpx.TimeoutException as exc:
            raise SpotifyProviderError(f"Spotify request timed out: {method} {url}") from exc
        except httpx.HTTPError as exc:
            raise SpotifyProviderError(f"Spotify request failed: {redact(exc)}") from exc
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After", "")
            raise SpotifyRateLimitError(f"Spotify rate limit exceeded; retry-after={retry_after}")
        if response.status_code in (401, 403):
            raise SpotifyAuthenticationError(
                f"Spotify authorization rejected ({response.status_code})"
            )
        if response.status_code >= 400:
            detail = self._error_detail(response)
            if response.status_code == 400 and "invalid_grant" in detail:
                raise SpotifyReauthorizationRequired(
                    "Spotify refresh authorization is no longer valid"
                )
            raise SpotifyProviderError(
                f"Spotify {method} {url} failed ({response.status_code}): {detail}"
            )
        return response

    @staticmethod
    def _error_detail(response: httpx.Response) -> str:
        try:
            value = response.json()
            if isinstance(value, dict):
                error = value.get("error", value)
                return redact(error)
        except ValueError:
            pass
        return redact(response.text[:300])
