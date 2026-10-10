# Data Model: BBC Radio Support

## BBC Radio Service

An immutable application catalog entry; only the nine entries in the spec are valid.

| Field | Type | Rules |
|---|---|---|
| `service_id` | `str` | Stable BBC RMS identifier; unique; allowlisted |
| `name` | `str` | Exact user-facing/Spotify playlist name from FR-001 |
| `format` | `str` | Descriptive music format from FR-001 |
| `logo_url` | `str | None` | Optional service-level image URL; never use segment artwork as a station logo |

The service ID is the grouping and managed-playlist identity. A programme/show name is optional
source metadata and never selects the playlist.

## BBC Music Play (normalized `SongRecord`)

| Field | Mapping / invariant |
|---|---|
| `track_id` | `bbc:{service_id}:{segment_id}`; use the segment `urn` only if the `id` is absent. This is the source event key for SQLite uniqueness. |
| `song` | Non-empty secondary/track title after RMS-specific mapping and validation. |
| `artist` | Non-empty primary/artist title after RMS-specific mapping and validation. |
| `album` | Optional normalized album metadata when present. |
| `captured_at` | UTC time this service response was collected; not represented as actual airtime. |
| `airdate` | Leave unset unless the endpoint supplies an absolute timezone-aware broadcast timestamp. |
| `play_type` | `trackplay` only for eligible music segment types; non-music items are discarded. |
| `raw_json` | Original segment fields plus normalized `bbc_service_id`, stable `source_order`, and any relative offset/labels. |
| `id` | Existing integer field is unset for BBC items; the event identity is carried in `track_id`. |

Missing station attribution is not repaired from programme names. Missing segment IDs, title,
artist, or a recognized music segment type make that segment ineligible and produce an
actionable station-scoped diagnostic. One malformed item does not discard valid siblings.

## BBC Station Playlist

Uses the existing Spotify managed playlist and `SongQueueItem` model with the following identity
conventions:

- Provider-neutral grouping key: `bbc:{service_id}`.
- Spotify display name: exact catalog `name`, without the KEXP prefix.
- Description: existing timezone-aware update format with a source-qualified BBC managed
  identity marker, preserving compatibility with current KEXP markers.
- Artwork: optional catalog logo only; unavailable artwork does not block track changes.
- Queue item: destination Spotify URI, source-qualified event key, station grouping key, and a
  stable source order that preserves RMS newest-first ordering. Queue uniqueness is by Spotify
  URI inside that station playlist.
- Limit: existing `spotify_playlist_limit` enforced independently per station; oldest tracks
  are removed first according to the queue's established newest-first playlist ordering.

No BBC aggregate playlist is created. No empty playlist is created when a station has no
eligible, resolvable records.

## Persistence and migration

No schema migration is planned. The current `songs.track_id` is already a unique text key, and
the normalized BBC key is namespaced to avoid collisions with KEXP. The `raw_json` column
retains service association and provider payload for later Spotify synchronization. Existing
KEXP `track_id` values, rows, and deduplication behavior remain unchanged.

## Run outcome

The combined command aggregates independent unit results. Each failed source/service or station
playlist operation adds a sanitized diagnostic containing the unit, operation, and failure
class. Successful units are retained. The execution record is marked failed and the CLI exits
nonzero if any unit failed; full success exits zero. Spotify auth/configuration and shared
database errors are run-wide failures.

