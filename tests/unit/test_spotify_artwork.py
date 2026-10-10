from base64 import b64encode
from importlib import resources

from kexp2spotify.spotify_artwork import SPOTIFY_COVER_PAYLOAD_LIMIT, prepare_cover


def test_bundled_latest_tracks_artwork_prepares_as_spotify_jpeg() -> None:
    image = (
        resources.files("kexp2spotify")
        .joinpath("assets")
        .joinpath("kexp-logo-black-on-orange.jpg")
        .read_bytes()
    )

    cover = prepare_cover(image)

    assert cover is not None
    assert cover.startswith(b"\xff\xd8\xff")
    assert len(b64encode(cover)) <= SPOTIFY_COVER_PAYLOAD_LIMIT


def test_prepare_cover_rejects_invalid_image_bytes() -> None:
    assert prepare_cover(b"not an image") is None
