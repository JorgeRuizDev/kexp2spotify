"""Spotify Web API adapter; provider details stay in this module."""

from __future__ import annotations

import base64
from collections.abc import Sequence
from typing import Any

import httpx

from .config import Settings
from .domain import ManagedPlaylist, Show
from .errors import SpotifyProviderError
from .ports import DestinationItem, MutationResult
from .spotify_http import SpotifyHttp

API_URL = "https://api.spotify.com/v1"


class SpotifyClient:
    def __init__(
        self, settings: Settings, access_token: str, http: SpotifyHttp | None = None
    ) -> None:
        self.settings = settings
        self.access_token = access_token
        self.http = http or SpotifyHttp(settings.request_timeout_seconds)

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        return self.http.request(method, f"{API_URL}{path}", token=self.access_token, **kwargs)

    def find_managed_playlist(self, show_id: str, expected_name: str) -> ManagedPlaylist | None:
        matches: list[dict[str, Any]] = []
        url: str | None = "/me/playlists?limit=50"
        while url:
            response = self._request("GET", url)
            body = response.json()
            for item in body.get("items", []):
                if item.get("name") == expected_name and item.get("id"):
                    matches.append(item)
            url = body.get("next")
            if url and url.startswith(API_URL):
                url = url[len(API_URL) :]
        if len(matches) > 1:
            raise SpotifyProviderError(f"ambiguous managed playlist for show {show_id}")
        if not matches:
            return None
        item = matches[0]
        return ManagedPlaylist(
            show_id=show_id,
            provider_playlist_id=str(item["id"]),
            name=str(item["name"]),
            description=str(item.get("description") or ""),
        )

    def create_playlist(self, show: Show, name: str, description: str) -> ManagedPlaylist:
        response = self._request(
            "POST",
            "/me/playlists",
            json={"name": name, "description": description, "public": False},
        )
        body = response.json()
        return ManagedPlaylist(
            show_id=show.id,
            provider_playlist_id=str(body["id"]),
            name=name,
            description=description,
        )

    def read_playlist_items(self, playlist_id: str) -> list[DestinationItem]:
        result: list[DestinationItem] = []
        url: str | None = (
            f"/playlists/{playlist_id}/items?limit=50&fields=items(item(track(uri,id)),added_at),next"
        )
        while url:
            body = self._request("GET", url).json()
            for position, item in enumerate(body.get("items", []), start=len(result)):
                track = item.get("item") or item.get("track") or {}
                uri = track.get("uri")
                if uri:
                    result.append(
                        DestinationItem(uri=str(uri), position=position, item_id=track.get("id"))
                    )
            url = body.get("next")
            if url and url.startswith(API_URL):
                url = url[len(API_URL) :]
        return result

    def append_items(self, playlist_id: str, track_uris: Sequence[str]) -> MutationResult:
        if not track_uris:
            return MutationResult(changed=False)
        last: str | None = None
        for start in range(0, len(track_uris), 100):
            response = self._request(
                "POST",
                f"/playlists/{playlist_id}/items",
                json={"uris": list(track_uris[start : start + 100])},
            )
            last = response.json().get("snapshot_id")
        return MutationResult(changed=True, snapshot_id=last)

    def remove_items(self, playlist_id: str, items: Sequence[DestinationItem]) -> MutationResult:
        if not items:
            return MutationResult(changed=False)
        response = self._request(
            "DELETE",
            f"/playlists/{playlist_id}/items",
            json={"tracks": [{"uri": item.uri} for item in items]},
        )
        return MutationResult(changed=True, snapshot_id=response.json().get("snapshot_id"))

    def update_details(self, playlist_id: str, name: str, description: str) -> MutationResult:
        self._request(
            "PUT", f"/playlists/{playlist_id}", json={"name": name, "description": description}
        )
        return MutationResult(changed=True)

    def resolve_track(self, query: str) -> str | None:
        response = self._request("GET", "/search", params={"q": query, "type": "track", "limit": 1})
        items = response.json().get("tracks", {}).get("items", [])
        return str(items[0]["uri"]) if items and items[0].get("uri") else None

    def update_cover(self, playlist_id: str, image_bytes: bytes) -> MutationResult:
        if len(image_bytes) > 256 * 1024 or not image_bytes.startswith(b"\xff\xd8\xff"):
            return MutationResult(changed=False)
        encoded = base64.b64encode(image_bytes)
        response = self._request(
            "PUT",
            f"/playlists/{playlist_id}/images",
            content=encoded,
            headers={"Content-Type": "image/jpeg"},
        )
        return MutationResult(changed=response.status_code in (200, 202))
