"""Safe, concise operational logging."""

import logging


def configure_logging() -> logging.Logger:
    """Configure and return the package logger."""

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    return logging.getLogger("kexp2spotify")
