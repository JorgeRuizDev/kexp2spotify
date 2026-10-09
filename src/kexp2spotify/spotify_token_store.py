"""Atomic, local persistence for Spotify refresh authorization."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from pydantic import ValidationError

from .domain import AuthorizationState
from .errors import SpotifyAuthenticationError


class FileTokenStore:
    """Persist tokens as JSON and replace them atomically."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> AuthorizationState:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            return AuthorizationState.model_validate(raw)
        except FileNotFoundError as exc:
            raise SpotifyAuthenticationError(f"Spotify token file is missing: {self.path}") from exc
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            raise SpotifyAuthenticationError(
                f"Spotify token file is corrupt or unreadable: {self.path}"
            ) from exc

    def save(self, state: AuthorizationState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=f".{self.path.name}.", dir=self.path.parent)
        temporary_path = Path(temporary)
        try:
            os.chmod(temporary_path, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(state.model_dump(mode="json"), handle, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, self.path)
            try:
                os.chmod(self.path, 0o600)
            except OSError:
                pass
        except OSError as exc:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise SpotifyAuthenticationError(
                f"could not persist Spotify token file: {self.path}"
            ) from exc
