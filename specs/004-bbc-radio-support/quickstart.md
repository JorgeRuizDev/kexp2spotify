# Quickstart: BBC Radio Support

## Requirements

- Existing KEXP2Spotify runtime and YAML configuration.
- Existing Spotify account setup with playlist read/modify and artwork scopes as configured by
  the project.
- Network access to `rms.api.bbc.co.uk`, BBC service image URLs when available, and Spotify.
- No BBC API key, BBC login, or BBC-specific configuration value.

The RMS latest-segments endpoint is observed in BBC Sounds traffic but is not documented by the
BBC as a supported external developer API. Its availability and response shape have no upstream
stability guarantee.

## Setup and run

1. Keep the current required configuration, including `fetch_limit`, request timeout, database
   path, Spotify playlist limit, timezone, and Spotify credentials/token setup.
2. Run the existing `spotify-login` command if Spotify has not been authorized or requires
   reauthorization.
3. Run `spotify-update` with the existing config. The command updates KEXP and then attempts all
   nine BBC music services. BBC requests use the configured `fetch_limit`, capped at the RMS
   maximum of 10 segments per service.
4. Read the structured log summary and scheduler exit code. A nonzero result means at least one
   unit failed; successful station/KEXP updates are retained and should not be duplicated on the
   next run.

## Expected Spotify playlists

BBC playlists are named exactly `BBC Radio 1`, `BBC Radio 1 Anthems`, `BBC Radio 1 Dance`,
`BBC Radio 1Xtra`, `BBC Radio 2`, `BBC Radio 3`, `BBC Radio 3 Unwind`, `BBC Radio 6 Music`,
and `BBC Radio 6 Indie Forever`. Each playlist groups tracks by radio service across shows.
Unsupported spoken-word, sports, and local/national radio services do not create BBC playlists.
The existing KEXP show playlists and Latest Tracks playlist continue as before.

BBC playlists use the same Spotify authorization, `fetch_limit`, playlist limit, and configured
timezone as KEXP. Artwork is applied only when a station-level logo URL is configured and
available; segment or track artwork is never substituted for station identity artwork.

## Failure behavior

Spotify configuration/authorization is checked before the run mutates playlists. A failure in
one BBC service does not prevent attempts for the other BBC services or KEXP. Missing station
logo artwork is non-fatal. The process records partial failure and exits nonzero after completing
the remaining units; inspect the service name and operation in logs, then rerun after resolving
the issue.

Permanent BBC HTTP 4xx errors are attempted once and logged with their HTTP status. Request
timeouts (408), early requests (425), rate limits (429), server errors (5xx), and transport
failures use the bounded retry policy. Spotify playlist limits remain governed by the separate
configured playlist limit.

