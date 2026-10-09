"""Typed errors exposed by the crawler layers."""


class KexpError(Exception):
    """Base class for expected operational failures."""


class ConfigurationError(KexpError):
    """Configuration is missing or invalid."""


class SourceError(KexpError):
    """The configured source could not provide a valid collection."""


class PersistenceError(KexpError):
    """The repository could not complete an operation."""
