"""Non-interactive cron entry point."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .bbc_catalog import BBC_SERVICES, BbcService
from .bbc_client import BbcClient
from .bbc_sync import synchronize_bbc_service
from .config import Settings, load_settings
from .crawler import collect
from .domain import SynchronizationResult
from .errors import (
    KexpError,
    NonRetryableSourceError,
    PersistenceError,
    SourceError,
    SpotifyError,
)
from .kexp_client import KexpClient
from .logging import configure_logging, redact
from .observability import (
    build_run_summary,
    daily_summary_message,
    failure_message,
    notifier_from_settings,
    previous_local_day,
    run_with_retries,
    safe_notify,
)
from .spotify_auth import SpotifyAuthenticator
from .spotify_client import SpotifyClient
from .spotify_sync import synchronize_records
from .sqlite_repository import SQLiteRepository


def main(argv: list[str] | None = None) -> int:
    """Run one crawl and return a cron-friendly exit code."""

    parser = argparse.ArgumentParser(
        description="Collect recent KEXP trackplays or update Spotify playlists"
    )
    parser.add_argument("command", nargs="?", choices=("spotify-login", "spotify-update"))
    parser.add_argument("--config", help="mandatory YAML configuration path")
    args = parser.parse_args(argv)
    logger = configure_logging()
    repository: SQLiteRepository | None = None
    try:
        settings = load_settings(args.config)
        logger = configure_logging(settings)
        if args.command == "spotify-login":
            SpotifyAuthenticator(settings).authorize_interactive()
            logger.info("spotify login completed without exposing credentials")
            return 0
        command = args.command or "crawl"
        repository = SQLiteRepository(settings.database_path)
        notifier = notifier_from_settings(settings)
        local_now = datetime.now(UTC)
        previous_day = previous_local_day(local_now, settings.spotify_timezone)
        if not repository.daily_summary_sent(previous_day):
            summary_message = daily_summary_message(
                previous_day, repository.daily_execution_summary(previous_day)
            )
            if safe_notify(notifier, logger, summary_message):
                repository.mark_daily_summary_sent(previous_day, local_now)

        started_at = local_now

        if command == "spotify-update":
            try:
                result, attempts = _synchronize_all_sources(settings, repository, logger)
            except Exception as exc:
                attempts = 1
                repository.record_execution(
                    started_at.astimezone(ZoneInfo(settings.spotify_timezone)).date(),
                    command,
                    started_at,
                    datetime.now(UTC),
                    "failed",
                    attempts,
                    error=str(exc),
                )
                safe_notify(notifier, logger, failure_message(command, attempts, exc))
                if isinstance(exc, KexpError):
                    logger.error("spotify update failed phase=preflight detail=%s", exc)
                else:
                    logger.exception("spotify update failed phase=preflight")
                return 1
            status = "success" if result.successful else "failed"
            error = "; ".join(result.failures) if result.failures else None
            repository.record_execution(
                started_at.astimezone(ZoneInfo(settings.spotify_timezone)).date(),
                command,
                started_at,
                datetime.now(UTC),
                status,
                attempts,
                build_run_summary(command, result),
                error=error,
            )
            logger.info(
                "spotify update complete status=%s shows=%d created=%d appended=%d "
                "removed=%d skipped=%d artwork_updated=%d artwork_preserved=%d "
                "artwork_unavailable=%d failures=%d",
                status,
                result.shows,
                result.created_playlists,
                result.appended_tracks,
                result.removed_tracks,
                result.skipped_tracks,
                result.artwork_updated,
                result.artwork_preserved,
                result.artwork_unavailable,
                len(result.failures),
            )
            if not result.successful:
                failure_error = KexpError(error or "one or more synchronization units failed")
                safe_notify(
                    notifier, logger, failure_message(command, attempts, failure_error)
                )
                return 1
            return 0

        def operation() -> object:
            source = KexpClient(settings)
            summary = collect(source, repository, settings.deduplication_window)
            logger.info(
                "crawl summary phase=complete received=%d eligible=%d discarded=%d "
                "duplicate=%d inserted=%d",
                summary.received,
                summary.eligible,
                summary.discarded,
                summary.duplicate,
                summary.inserted,
            )
            return summary

        try:
            result, attempts = run_with_retries(operation)
            repository.record_execution(
                started_at.astimezone(ZoneInfo(settings.spotify_timezone)).date(),
                command,
                started_at,
                datetime.now(UTC),
                "success",
                attempts,
                build_run_summary(command, result),
            )
            return 0
        except Exception as exc:
            attempts = 4
            repository.record_execution(
                started_at.astimezone(ZoneInfo(settings.spotify_timezone)).date(),
                command,
                started_at,
                datetime.now(UTC),
                "failed",
                attempts,
                error=str(exc),
            )
            safe_notify(notifier, logger, failure_message(command, attempts, exc))
            if isinstance(exc, KexpError):
                logger.error("crawl failed phase=operational detail=%s", exc)
            else:
                logger.exception("crawl failed phase=unexpected")
            return 1
    except KexpError as exc:
        logger.error("crawl failed phase=operational detail=%s", exc)
        return 1
    finally:
        if repository is not None:
            repository.close()


def _synchronize_all_sources(
    settings: Settings,
    repository: SQLiteRepository,
    logger: logging.Logger,
) -> tuple[SynchronizationResult, int]:
    """Preflight Spotify once, then retry each source or station independently."""

    try:
        ZoneInfo(settings.spotify_timezone)
    except ZoneInfoNotFoundError as exc:
        raise KexpError(f"invalid Spotify timezone: {settings.spotify_timezone}") from exc
    authenticator = SpotifyAuthenticator(settings)
    authenticator.load_and_refresh()
    if not authenticator.last_access_token:
        raise KexpError("Spotify did not return an access token")
    destination = SpotifyClient(settings, authenticator.last_access_token)
    kexp_source = KexpClient(settings)
    bbc_source = BbcClient(settings)
    result = SynchronizationResult()
    attempts_total = 0

    def kexp_operation() -> SynchronizationResult:
        plays = kexp_source.fetch_plays()
        summary = collect(
            type("CurrentBatch", (), {"fetch_plays": lambda self: plays})(),
            repository,
            settings.deduplication_window,
        )
        logger.info(
            "KEXP collection complete received=%d eligible=%d discarded=%d "
            "duplicate=%d inserted=%d",
            summary.received,
            summary.eligible,
            summary.discarded,
            summary.duplicate,
            summary.inserted,
        )
        return synchronize_records(
            kexp_source,
            destination,
            destination,
            summary.records,
            settings,
            playlist_store=repository,
        )

    current, attempts = _run_sync_unit("KEXP", kexp_operation, logger)
    attempts_total += attempts
    result = _combine_results(result, current)

    for service in BBC_SERVICES:
        current, attempts = _run_sync_unit(
            f"BBC {service.service_id}",
            _make_bbc_operation(bbc_source, destination, service, settings, repository),
            logger,
        )
        attempts_total += attempts
        result = _combine_results(result, current)

    return result, attempts_total


def _make_bbc_operation(
    source: BbcClient,
    destination: SpotifyClient,
    service: BbcService,
    settings: Settings,
    repository: SQLiteRepository,
) -> Callable[[], SynchronizationResult]:
    def operation() -> SynchronizationResult:
        return synchronize_bbc_service(
            source,
            destination,
            destination,
            service,
            settings,
            repository=repository,
            playlist_store=repository,
        )

    return operation


def _run_sync_unit(
    name: str,
    operation: Callable[[], SynchronizationResult],
    logger: logging.Logger,
) -> tuple[SynchronizationResult, int]:
    attempts = 0

    def tracked_operation() -> SynchronizationResult:
        nonlocal attempts
        attempts += 1
        return operation()

    try:
        result, attempts = run_with_retries(
            tracked_operation,
            retry_if=lambda exc: not isinstance(exc, NonRetryableSourceError),
        )
        if not isinstance(result, SynchronizationResult):
            raise TypeError(f"{name} synchronization returned an invalid result")
        if name == "KEXP":
            logger.info(
                "KEXP synchronization complete attempts=%d shows=%d appended=%d "
                "removed=%d skipped=%d",
                attempts,
                result.shows,
                result.appended_tracks,
                result.removed_tracks,
                result.skipped_tracks,
            )
        return result, attempts
    except PersistenceError:
        raise
    except Exception as exc:
        detail = (
            redact(exc)
            if isinstance(exc, (SourceError, SpotifyError))
            else type(exc).__name__
        )
        logger.error(
            "synchronization unit failed unit=%s operation=update attempts=%d "
            "error_type=%s error=%s",
            name,
            attempts,
            type(exc).__name__,
            detail,
        )
        return (
            SynchronizationResult(
                failures=[f"{name} synchronization failed: {detail}"]
            ),
            attempts,
        )


def _combine_results(
    total: SynchronizationResult, current: SynchronizationResult
) -> SynchronizationResult:
    return SynchronizationResult(
        shows=total.shows + current.shows,
        created_playlists=total.created_playlists + current.created_playlists,
        updated_playlists=total.updated_playlists + current.updated_playlists,
        appended_tracks=total.appended_tracks + current.appended_tracks,
        removed_tracks=total.removed_tracks + current.removed_tracks,
        skipped_tracks=total.skipped_tracks + current.skipped_tracks,
        artwork_updated=total.artwork_updated + current.artwork_updated,
        artwork_preserved=total.artwork_preserved + current.artwork_preserved,
        artwork_unavailable=total.artwork_unavailable + current.artwork_unavailable,
        failures=total.failures + current.failures,
        reauthorization_required=(
            total.reauthorization_required or current.reauthorization_required
        ),
    )


if __name__ == "__main__":
    sys.exit(main())
