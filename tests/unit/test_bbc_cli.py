import time
from pathlib import Path
from types import SimpleNamespace

import pytest

import kexp2spotify.cli as cli
from kexp2spotify.bbc_catalog import get_bbc_service
from kexp2spotify.config import Settings
from kexp2spotify.domain import SynchronizationResult
from kexp2spotify.errors import NonRetryableSourceError, SourceError, SpotifyProviderError


class FakeRepository:
    def __init__(self) -> None:
        self.inserted = []

    def insert_many(self, records):
        self.inserted.extend(records)
        return len(records)


class FakeAuthenticator:
    created = 0

    def __init__(self, settings: Settings) -> None:
        FakeAuthenticator.created += 1
        self.last_access_token = "access-token"

    def load_and_refresh(self) -> None:
        return None


class FakeSource:
    def fetch_plays(self):
        return []


def test_cli_update_attempts_each_station_after_failure_and_authenticates_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = Settings(
        kexp_plays_url="https://example.com/plays", fetch_limit=2,
        deduplication_window=10, database_path=tmp_path / "db.sqlite",
        request_timeout_seconds=2, config_file=tmp_path / "config.yml",
    )
    repo = FakeRepository()
    FakeAuthenticator.created = 0
    service_one = get_bbc_service("bbc_radio_one")
    service_two = get_bbc_service("bbc_radio_two")
    assert service_one is not None and service_two is not None
    monkeypatch.setattr(cli, "SpotifyAuthenticator", FakeAuthenticator)
    monkeypatch.setattr(cli, "SpotifyClient", lambda *args: object())
    monkeypatch.setattr(cli, "KexpClient", lambda settings: FakeSource())
    monkeypatch.setattr(cli, "BbcClient", lambda settings: object())
    monkeypatch.setattr(cli, "BBC_SERVICES", (service_one, service_two))
    monkeypatch.setattr(
        cli,
        "collect",
        lambda source, repository, window: SimpleNamespace(
            records=[], received=0, eligible=0, discarded=0, duplicate=0, inserted=0
        ),
    )
    monkeypatch.setattr(
        cli, "synchronize_records", lambda *args, **kwargs: SynchronizationResult(shows=1)
    )
    attempted: list[str] = []

    def sync_bbc(source, destination, resolver, service, settings, **kwargs):
        attempted.append(service.service_id)
        if service.service_id == service_one.service_id:
            raise RuntimeError("BBC timeout")
        return SynchronizationResult(shows=1)

    monkeypatch.setattr(cli, "synchronize_bbc_service", sync_bbc)

    def immediate_retries(operation, attempts=4, delay_seconds=1.0, retry_if=None):
        for count in range(1, attempts + 1):
            try:
                return operation(), count
            except Exception as exc:
                if count == attempts or (retry_if is not None and not retry_if(exc)):
                    raise
        raise AssertionError("unreachable")

    monkeypatch.setattr(cli, "run_with_retries", immediate_retries)
    result, attempts = cli._synchronize_all_sources(settings, repo, cli.logging.getLogger("test"))

    assert FakeAuthenticator.created == 1
    assert attempted == [service_one.service_id] * 4 + [service_two.service_id]
    assert result.shows == 2
    assert not result.successful
    assert len(result.failures) == 1
    assert attempts == 1 + 4 + 1


def test_cli_does_not_retry_permanent_source_errors_and_reports_detail(
    caplog: pytest.LogCaptureFixture,
) -> None:
    calls = 0

    def fail_permanently() -> SynchronizationResult:
        nonlocal calls
        calls += 1
        raise NonRetryableSourceError(
            "BBC station bbc_radio_one latest segments returned HTTP 400"
        )

    result, attempts = cli._run_sync_unit(
        "BBC bbc_radio_one", fail_permanently, cli.logging.getLogger("test")
    )

    assert calls == 1
    assert attempts == 1
    assert result.failures == [
        "BBC bbc_radio_one synchronization failed: "
        "BBC station bbc_radio_one latest segments returned HTTP 400"
    ]
    assert "attempts=1" in caplog.text
    assert "HTTP 400" in caplog.text


def test_cli_reports_safe_detail_after_retryable_source_failure(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = 0

    def fail_temporarily() -> SynchronizationResult:
        nonlocal calls
        calls += 1
        raise SourceError("BBC station bbc_radio_one latest segments returned HTTP 503")

    monkeypatch.setattr(time, "sleep", lambda _delay: None)
    result, attempts = cli._run_sync_unit(
        "BBC bbc_radio_one", fail_temporarily, cli.logging.getLogger("test")
    )

    assert calls == 4
    assert attempts == 4
    assert result.failures == [
        "BBC bbc_radio_one synchronization failed: "
        "BBC station bbc_radio_one latest segments returned HTTP 503"
    ]
    assert "attempts=4" in caplog.text
    assert "HTTP 503" in caplog.text


def test_cli_reports_redacted_spotify_provider_detail(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(time, "sleep", lambda _delay: None)

    def fail() -> SynchronizationResult:
        raise SpotifyProviderError(
            "Spotify DELETE /playlists/playlist/items failed (400): invalid items payload"
        )

    result, attempts = cli._run_sync_unit(
        "BBC bbc_radio_one", fail, cli.logging.getLogger("test")
    )

    assert attempts == 4
    assert result.failures == [
        "BBC bbc_radio_one synchronization failed: "
        "Spotify DELETE /playlists/playlist/items failed (400): invalid items payload"
    ]
    assert "error_type=SpotifyProviderError" in caplog.text
    assert "failed (400): invalid items payload" in caplog.text
