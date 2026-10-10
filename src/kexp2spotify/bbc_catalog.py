"""Fixed allowlist of BBC music services supported by the integration."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BbcService:
    service_id: str
    name: str
    format: str
    logo_url: str | None = None
    logo_asset: str | None = None


BBC_SERVICES: tuple[BbcService, ...] = (
    BbcService(
        "bbc_radio_one",
        "BBC Radio 1",
        "Youth-orientated music",
        logo_asset="bbc-radio-1.png",
    ),
    BbcService(
        "bbc_radio_one_anthems",
        "BBC Radio 1 Anthems",
        "Nostalgic and classic popular music",
        logo_asset="bbc-radio-1-anthems.png",
    ),
    BbcService(
        "bbc_radio_one_dance",
        "BBC Radio 1 Dance",
        "Electronic dance music",
        logo_asset="bbc-radio-1.png",
    ),
    BbcService(
        "bbc_1xtra",
        "BBC Radio 1Xtra",
        "Black contemporary music",
        logo_asset="bbc-radio-1.png",
    ),
    BbcService(
        "bbc_radio_two",
        "BBC Radio 2",
        "Adult-orientated music",
        logo_asset="bbc-radio-2.png",
    ),
    BbcService(
        "bbc_radio_three",
        "BBC Radio 3",
        "Classical, jazz, world music and culture",
        logo_asset="bbc-radio-3.png",
    ),
    BbcService(
        "bbc_radio_three_unwind",
        "BBC Radio 3 Unwind",
        "Classical and meditation music",
        logo_asset="bbc-radio-3.png",
    ),
    BbcService(
        "bbc_6music",
        "BBC Radio 6 Music",
        "Alternative music",
        logo_asset="bbc-radio-6-music.png",
    ),
    BbcService(
        "bbc_radio_six_indie_forever",
        "BBC Radio 6 Indie Forever",
        "Indie music",
        logo_asset="bbc-radio-6-music.png",
    ),
)

_SERVICE_BY_ID = {service.service_id: service for service in BBC_SERVICES}


def get_bbc_service(service_id: str) -> BbcService | None:
    """Return a supported service, never dynamically accepting arbitrary BBC IDs."""

    return _SERVICE_BY_ID.get(service_id)
