"""Prepare custom playlist artwork for Spotify's image upload endpoint."""

from __future__ import annotations

import base64
from io import BytesIO

from PIL import Image, UnidentifiedImageError

SPOTIFY_COVER_PAYLOAD_LIMIT = 256 * 1024


def prepare_cover(image_bytes: bytes) -> bytes | None:
    """Return a valid JPEG whose Base64 request body meets Spotify's size limit."""

    try:
        with Image.open(BytesIO(image_bytes)) as source:
            image = source.convert("RGB")
        image.thumbnail((640, 640))
        for quality in (90, 85, 80, 75, 70, 65, 60, 55, 50):
            output = BytesIO()
            image.save(output, format="JPEG", quality=quality, optimize=True)
            encoded = output.getvalue()
            if len(base64.b64encode(encoded)) <= SPOTIFY_COVER_PAYLOAD_LIMIT:
                return encoded
    except (OSError, ValueError, UnidentifiedImageError):
        return None
    return None
