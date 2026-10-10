"""Stable metadata shared by Spotify playlist creation and discovery."""

DESCRIPTION_SUFFIX = " ·  github.com/JorgeRuizDev/kexp2spotify"
IDENTITY_MARKER_PREFIX = "[kexp2spotify-show:"
BBC_IDENTITY_MARKER_PREFIX = "[kexp2spotify-bbc:"


def playlist_identity_marker(show_id: str) -> str:
    if show_id.startswith("bbc:"):
        return f"{BBC_IDENTITY_MARKER_PREFIX}{show_id.removeprefix('bbc:')}]"
    return f"{IDENTITY_MARKER_PREFIX}{show_id}]"


def has_playlist_identity(description: str) -> bool:
    return IDENTITY_MARKER_PREFIX in description or BBC_IDENTITY_MARKER_PREFIX in description
