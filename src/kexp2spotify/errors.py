"""Typed errors exposed by the crawler layers."""


class KexpError(Exception):
    """Base class for expected operational failures."""


class ConfigurationError(KexpError):
    """Configuration is missing or invalid."""


class SourceError(KexpError):
    """The configured source could not provide a valid collection."""


class NonRetryableSourceError(SourceError):
    """The source rejected a request that will not succeed if repeated unchanged."""


class PersistenceError(KexpError):
    """The repository could not complete an operation."""


class SpotifyError(KexpError):
    """Base class for expected Spotify integration failures."""


class SpotifyAuthenticationError(SpotifyError):
    """Authorization is missing, invalid, or requires operator action."""


class SpotifyScopeError(SpotifyError):
    """The authorization does not grant a required scope."""


class SpotifyProviderError(SpotifyError):
    """Spotify returned an operational or validation error."""


class SpotifyRateLimitError(SpotifyProviderError):
    """Spotify asked the caller to retry after a delay."""


class SpotifyPlaylistAmbiguousError(SpotifyProviderError):
    """More than one managed playlist matched a show."""


class SpotifyTrackUnresolvedError(SpotifyProviderError):
    """A source song could not be resolved to a Spotify track."""


class SpotifyReauthorizationRequired(SpotifyAuthenticationError):
    """The persisted refresh token cannot be used anymore."""
