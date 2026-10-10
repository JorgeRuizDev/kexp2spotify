from kexp2spotify.bbc_catalog import BBC_SERVICES, get_bbc_service


def test_catalog_has_exact_nine_requested_services() -> None:
    assert [(service.service_id, service.name, service.format) for service in BBC_SERVICES] == [
        ("bbc_radio_one", "BBC Radio 1", "Youth-orientated music"),
        ("bbc_radio_one_anthems", "BBC Radio 1 Anthems", "Nostalgic and classic popular music"),
        ("bbc_radio_one_dance", "BBC Radio 1 Dance", "Electronic dance music"),
        ("bbc_1xtra", "BBC Radio 1Xtra", "Black contemporary music"),
        ("bbc_radio_two", "BBC Radio 2", "Adult-orientated music"),
        ("bbc_radio_three", "BBC Radio 3", "Classical, jazz, world music and culture"),
        ("bbc_radio_three_unwind", "BBC Radio 3 Unwind", "Classical and meditation music"),
        ("bbc_6music", "BBC Radio 6 Music", "Alternative music"),
        ("bbc_radio_six_indie_forever", "BBC Radio 6 Indie Forever", "Indie music"),
    ]


def test_catalog_rejects_spoken_word_sports_local_and_unknown_services() -> None:
    for service_id in (
        "bbc_radio_four",
        "bbc_radio_four_extra",
        "bbc_radio_five_live",
        "bbc_radio_five_live_sports_extra",
        "bbc_radio_cumbria",
        "unknown",
    ):
        assert get_bbc_service(service_id) is None
