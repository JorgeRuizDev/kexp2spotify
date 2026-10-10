from datetime import UTC, datetime

from kexp2spotify.bbc_client import normalize_segment


def test_normalization_qualifies_identity_and_maps_artist_and_title() -> None:
    now = datetime(2026, 10, 10, 10, tzinfo=UTC)
    segment = {
        "id": "p01",
        "urn": "urn:bbc:radio:segment:music:other",
        "segment_type": "music",
        "titles": {"primary": "Artist", "secondary": "Song"},
        "offset": {"start": 30, "label": "2 minutes ago"},
    }
    record = normalize_segment(segment, "bbc_radio_one", now, 4)
    assert record is not None
    assert record.track_id == "bbc:bbc_radio_one:p01"
    assert record.artist == "Artist"
    assert record.song == "Song"
    assert record.id is None
    assert record.captured_at == now
    assert record.airdate is None
    assert record.play_type == "trackplay"
    assert record.raw_json["bbc_service_id"] == "bbc_radio_one"
    assert record.raw_json["source_order"] == 4
    assert record.raw_json["offset"] == {"start": 30, "label": "2 minutes ago"}


def test_normalization_uses_urn_only_when_segment_id_missing() -> None:
    segment = {
        "urn": "urn:bbc:radio:segment:music:fallback",
        "segment_type": "music",
        "titles": {"primary": "Artist", "secondary": "Song"},
    }
    record = normalize_segment(segment, "bbc_radio_two", datetime.now(UTC), 0)
    assert record is not None
    assert record.track_id == "bbc:bbc_radio_two:urn:bbc:radio:segment:music:fallback"


def test_normalization_rejects_non_music_and_malformed_segments() -> None:
    now = datetime.now(UTC)
    assert normalize_segment({"segment_type": "ident"}, "bbc_radio_one", now, 0) is None
    assert normalize_segment({"segment_type": "music"}, "bbc_radio_one", now, 1) is None
    assert normalize_segment(
        {
            "id": "bad",
            "segment_type": "music",
            "titles": {"primary": "Artist", "secondary": "  "},
        },
        "bbc_radio_one",
        now,
        2,
    ) is None


def test_airdate_accepts_only_absolute_timezone_aware_values() -> None:
    base = {
        "id": "time",
        "segment_type": "music",
        "titles": {"primary": "Artist", "secondary": "Song"},
    }
    relative = normalize_segment(
        {**base, "airdate": "2 minutes ago"}, "bbc_radio_one", datetime.now(UTC), 0
    )
    absolute = normalize_segment(
        {**base, "airdate": "2026-10-10T10:30:00+01:00"},
        "bbc_radio_one",
        datetime.now(UTC),
        1,
    )
    naive = normalize_segment(
        {**base, "airdate": "2026-10-10T10:30:00"}, "bbc_radio_one", datetime.now(UTC), 2
    )
    assert relative is not None and relative.airdate is None
    assert absolute is not None
    assert absolute.airdate == datetime.fromisoformat("2026-10-10T10:30:00+01:00")
    assert naive is not None and naive.airdate is None
