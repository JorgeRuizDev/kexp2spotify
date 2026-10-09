"""Non-interactive cron entry point."""

from __future__ import annotations

import argparse
import sys

from .config import load_settings
from .crawler import collect
from .errors import KexpError
from .kexp_client import KexpClient
from .logging import configure_logging
from .sqlite_repository import SQLiteRepository


def main(argv: list[str] | None = None) -> int:
    """Run one crawl and return a cron-friendly exit code."""

    parser = argparse.ArgumentParser(description="Collect recent KEXP trackplays")
    parser.add_argument("--config", help="mandatory YAML configuration path")
    args = parser.parse_args(argv)
    logger = configure_logging()
    repository: SQLiteRepository | None = None
    try:
        settings = load_settings(args.config)
        source = KexpClient(settings)
        repository = SQLiteRepository(settings.database_path)
        summary = collect(source, repository, settings.deduplication_window)
        logger.info("crawl summary phase=complete received=%d eligible=%d discarded=%d duplicate=%d inserted=%d",
                    summary.received, summary.eligible, summary.discarded, summary.duplicate, summary.inserted)
        return 0
    except KexpError as exc:
        logger.error("crawl failed phase=operational detail=%s", exc)
        return 1
    finally:
        if repository is not None:
            repository.close()


if __name__ == "__main__":
    sys.exit(main())
