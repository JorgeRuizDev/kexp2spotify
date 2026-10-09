"""Safe, concise operational logging."""

import logging
import re

_SECRET_PATTERN = re.compile(
    r"(?i)(access_token|refresh_token|client_secret|authorization|code)=([^&\s,]+)"
)


def redact(value: object) -> str:
    """Return diagnostic text with common credential fields removed."""

    return _SECRET_PATTERN.sub(r"\1=<redacted>", str(value))


def configure_logging() -> logging.Logger:
    """Configure and return the package logger."""

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    return logging.getLogger("kexp2spotify")
