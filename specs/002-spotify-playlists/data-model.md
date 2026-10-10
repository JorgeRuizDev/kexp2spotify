# Data Model: Spotify Show Playlists

## Show

Represents the stable show identity supplied by the source pipeline.

| Field | Type | Rules |
|---|---|---|
| `show_id` | string | Required, stable, non-empty; primary association key. |
| `name` | string | Required after trimming; used in the display name `KEXP - <show name>`. |
| `image` | binary or provider-ready image reference | Optional; when present, used for the playlist cover. |
| `timezone` | IANA timezone name | Optional per show; falls back to configured execution timezone. |

## SongQueueItem

Represents one eligible song in a show’s ordered queue.

| Field | Type | Rules |
|---|---|---|
| `show_id` | string | Must reference a Show. |
| `track_id` | string | Required source identity; used for duplicate detection. |
| `destination_uri` | string | Resolved Spotify track URI/ID; unresolved songs are reported and not appended. |
| `queued_at` | datetime | Time used for chronological ordering; timezone-aware. |
| `source_id` | string or null | Optional source play identity for diagnostics. |

Ordering is ascending by `queued_at`, with a deterministic secondary key such as `source_id`/`track_id`. Existing playlist order is authoritative for already-managed items; repeated songs do not move to the tail.

## ManagedPlaylist

Represents a destination playlist associated with a Show or with the fixed cross-show identity `kexp-latest-tracks`.

| Field | Type | Rules |
|---|---|---|
| `show_id` | string | Unique association; prevents duplicate managed playlists. The aggregate playlist uses the reserved identity `kexp-latest-tracks`. |
| `provider_playlist_id` | string | Persisted/provider-discovered Spotify playlist identifier. |
| `name` | string | Exactly `KEXP - <normalized show name>`. |
| `description` | string | Required generated template with execution time and timezone. |
| `track_uris` | ordered list[string] | No duplicates; length must not exceed configured limit after reconciliation. |
| `image_state` | enum | `updated`, `preserved`, or `unavailable`. |

The aggregate playlist is named exactly `KEXP - Latest Tracks`. Its queue combines resolved tracks from every show in the current input batch, uses the same configured limit as show playlists, and orders new tracks by play time from newest to oldest. Repeated destination tracks are not duplicated. Its default cover is the KEXP logo image supplied with the feature; the source image is converted to an uploadable JPEG within Spotify's size limit.

## AuthorizationState

Represents persisted permission for unattended calls.

| Field | Type | Rules |
|---|---|---|
| `client_id` | string | Required; never logged. |
| `refresh_token` | secret string | Required after login; stored outside source control and redacted everywhere. |
| `scope` | set[string] | Granted scopes; preflight checks required scopes. |
| `obtained_at` | datetime | Used for operator diagnostics and re-login reminders. |
| `last_refresh_at` | datetime or null | Updated after successful refresh. |
| `status` | enum | `valid`, `reauthorization_required`, or `invalid_configuration`. |

## SynchronizationResult

Per-run result used for logs and exit status: show count, created playlists, updated playlists, appended tracks, removed oldest tracks, skipped/unresolved tracks, artwork outcomes, reauthorization status, provider failures, and whether the run completed successfully. It MUST NOT contain secrets or full authorization responses.

## State transitions

```text
No authorization -> Login command -> Valid authorization
Valid authorization -> Access refresh -> Valid authorization
Valid authorization -> invalid_grant/revocation -> Reauthorization required
No managed playlist -> Create -> Managed playlist
Managed playlist -> Reconcile queue -> Updated managed playlist
Provider/config failure before mutation -> Existing state preserved
```
