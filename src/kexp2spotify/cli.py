"""Non-interactive cron entry point."""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from .config import load_settings
from .crawler import collect
from .errors import KexpError
from .kexp_client import KexpClient
from .logging import configure_logging
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

        def operation() -> object:
            if command == "spotify-update":
                source = KexpClient(settings)
                plays = source.fetch_plays()
                summary = collect(
                    type("CurrentBatch", (), {"fetch_plays": lambda self: plays})(),
                    repository,
                    settings.deduplication_window,
                )
                authenticator = SpotifyAuthenticator(settings)
                authenticator.load_and_refresh()
                if not authenticator.last_access_token:
                    raise KexpError("Spotify did not return an access token")
                destination = SpotifyClient(settings, authenticator.last_access_token)
                sync = synchronize_records(
                    source, destination, destination, summary.records, settings,
                    playlist_store=repository,
                )
                logger.info(
                    "spotify update complete shows=%d created=%d appended=%d removed=%d skipped=%d "
                    "artwork_updated=%d artwork_preserved=%d artwork_unavailable=%d",
                    sync.shows, sync.created_playlists, sync.appended_tracks, sync.removed_tracks,
                    sync.skipped_tracks, sync.artwork_updated, sync.artwork_preserved,
                    sync.artwork_unavailable,
                )
                return sync
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


if __name__ == "__main__":
    sys.exit(main())
