"""Safe, concise operational logging with a configurable rotating file."""

import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import Settings

_SECRET_PATTERN = re.compile(
    r"(?i)(access_token|refresh_token|client_secret|authorization|code)=([^&\s,]+)"
)


def redact(value: object) -> str:
    """Return diagnostic text with common credential fields removed."""

    return _SECRET_PATTERN.sub(r"\1=<redacted>", str(value))


def configure_logging(settings: "Settings | None" = None) -> logging.Logger:
    """Configure and return the package logger.

    The default configuration keeps CLI diagnostics on stderr and writes a
    timestamped, rotating log under ``data/``. Passing settings applies the
    configured path, level and rotation options.
    """

    log_file_path = Path("data/kexp2spotify.log")
    log_level_name = "INFO"
    max_bytes = 10_485_760
    backup_count = 5
    console_enabled = True
    if settings is not None:
        log_file_path = settings.log_file_path
        log_level_name = settings.log_level
        max_bytes = settings.log_file_max_bytes
        backup_count = settings.log_file_backup_count
        console_enabled = settings.log_console

    logger = logging.getLogger("kexp2spotify")
    logger.setLevel(getattr(logging, log_level_name))
    logger.propagate = False
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    if console_enabled:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger
