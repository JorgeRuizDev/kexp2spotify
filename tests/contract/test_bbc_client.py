import json
from pathlib import Path

import httpx
import pytest

from kexp2spotify.bbc_client import BbcClient
from kexp2spotify.config import Settings
from kexp2spotify.errors import NonRetryableSourceError, SourceError
from kexp2spotify.ports import BbcLatestSegmentsRequest


def _settings(tmp_path: Path, fetch_limit: int = 3) -> Settings:
    return Settings(
        kexp_plays_url="https://example.com/plays",
        fetch_limit=fetch_limit,
        deduplication_window=10,
        database_path=tmp_path / "db.sqlite",
        request_timeout_seconds=2.5,
        config_file=tmp_path / "config.yml",
    )


def test_client_uses_observed_request_shape_and_normalizes_fixture(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fixture = json.loads(Path("tests/contract/fixtures/bbc_rms_latest.json").read_text())

    def fake_get(url: str, **kwargs: object) -> httpx.Response:
        assert url == (
            "https://rms.api.bbc.co.uk/v2/services/bbc_radio_one/segments/latest"
        )
        assert kwargs["params"] == {"experience": "domestic", "offset": 0, "limit": 3}
        assert kwargs["timeout"] == 2.5
        return httpx.Response(200, json=fixture)

    monkeypatch.setattr(httpx, "get", fake_get)
    records = BbcClient(_settings(tmp_path)).fetch_latest_segments(
        BbcLatestSegmentsRequest("bbc_radio_one")
    )
    assert len(records) == 2
    assert records[0].track_id == "bbc:bbc_radio_one:p0gnbhlc"


def test_client_caps_rms_page_limit_at_ten(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fixture = json.loads(Path("tests/contract/fixtures/bbc_rms_latest.json").read_text())

    def fake_get(url: str, **kwargs: object) -> httpx.Response:
        assert kwargs["params"] == {"experience": "domestic", "offset": 0, "limit": 10}
        return httpx.Response(200, json=fixture)

    monkeypatch.setattr(httpx, "get", fake_get)
    records = BbcClient(_settings(tmp_path, fetch_limit=50)).fetch_latest_segments(
        BbcLatestSegmentsRequest("bbc_radio_one")
    )
    assert len(records) == 2


@pytest.mark.parametrize("status", [403, 429, 503])
def test_client_reports_http_status(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, status: int
) -> None:
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: httpx.Response(status))
    with pytest.raises(SourceError, match=f"HTTP {status}"):
        BbcClient(_settings(tmp_path)).fetch_latest_segments(
            BbcLatestSegmentsRequest("bbc_radio_one")
        )


@pytest.mark.parametrize("status", [408, 425, 429, 503])
def test_client_leaves_transient_http_errors_retryable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, status: int
) -> None:
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: httpx.Response(status))
    with pytest.raises(SourceError, match=f"HTTP {status}") as error:
        BbcClient(_settings(tmp_path)).fetch_latest_segments(
            BbcLatestSegmentsRequest("bbc_radio_one")
        )
    assert not isinstance(error.value, NonRetryableSourceError)


@pytest.mark.parametrize("status", [400, 403, 404])
def test_client_marks_permanent_http_errors_non_retryable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, status: int
) -> None:
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: httpx.Response(status))
    with pytest.raises(NonRetryableSourceError, match=f"HTTP {status}"):
        BbcClient(_settings(tmp_path)).fetch_latest_segments(
            BbcLatestSegmentsRequest("bbc_radio_one")
        )


@pytest.mark.parametrize("payload", [{"wrong": []}, {"data": "wrong"}, [1, 2]])
def test_client_rejects_malformed_collection(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, payload: object
) -> None:
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: httpx.Response(200, json=payload))
    with pytest.raises(SourceError, match="unsupported collection shape"):
        BbcClient(_settings(tmp_path)).fetch_latest_segments(
            BbcLatestSegmentsRequest("bbc_radio_one")
        )


def test_client_rejects_non_allowlisted_station(tmp_path: Path) -> None:
    with pytest.raises(SourceError, match="unsupported BBC service"):
        BbcClient(_settings(tmp_path)).fetch_latest_segments(
            BbcLatestSegmentsRequest("bbc_radio_four")
        )


def test_client_wraps_request_timeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def timeout(*args: object, **kwargs: object) -> httpx.Response:
        raise httpx.TimeoutException("request timed out")

    monkeypatch.setattr(httpx, "get", timeout)
    with pytest.raises(SourceError, match="TimeoutException"):
        BbcClient(_settings(tmp_path)).fetch_latest_segments(
            BbcLatestSegmentsRequest("bbc_radio_one")
        )
