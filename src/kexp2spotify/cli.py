"""Non-interactive cron entry point."""

from __future__ import annotations

import argparse
import sys

from .config import load_settings
from .crawler import collect
from .errors import KexpError
from .kexp_client import KexpClient
from .logging import configure_logging
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
        if args.command == "spotify-login":
            SpotifyAuthenticator(settings).authorize_interactive()
            logger.info("spotify login completed without exposing credentials")
            return 0
        if args.command == "spotify-update":
            source = KexpClient(settings)
            repository = SQLiteRepository(settings.database_path)
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
            sync = synchronize_records(source, destination, destination, summary.records, settings)
            logger.info(
                "spotify update complete shows=%d created=%d appended=%d removed=%d skipped=%d "
                "artwork_updated=%d artwork_preserved=%d artwork_unavailable=%d",
                sync.shows,
                sync.created_playlists,
                sync.appended_tracks,
                sync.removed_tracks,
                sync.skipped_tracks,
                sync.artwork_updated,
                sync.artwork_preserved,
                sync.artwork_unavailable,
            )
            return 0
        source = KexpClient(settings)
        repository = SQLiteRepository(settings.database_path)
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
        return 0
    except KexpError as exc:
        logger.error("crawl failed phase=operational detail=%s", exc)
        return 1
    finally:
        if repository is not None:
            repository.close()


if __name__ == "__main__":
    sys.exit(main())
