# Data Model: KEXP Play Crawler

## SongRecord

Represents a valid `trackplay` play prepared for the pipeline.

| Field | Type | Required | Rules |
|---|---|---:|---|
| `id` | integer | yes | KEXP play identifier; retained as auxiliary data |
| `track_id` | string | yes | Canonical deduplication key derived from `track_id`, falling back to `recording_id` and then play `id` |
| `song` | string | yes | Song name; non-empty |
| `artist` | string | yes | Artist; non-empty |
| `album` | string/null | no | Retained as empty/null when absent |
| `release_date` | date/string null | no | Retains the normalized original value when valid |
| `captured_at` | datetime | yes | UTC timestamp of local ingestion |
| `raw_json` | JSON text | yes | Complete received object, preserving unknown fields |
| `airdate` | datetime/string null | no | Provider air date, extracted when present |
| `play_type` | string | yes | Must be exactly `trackplay` |

## Constraints

- `track_id` has a unique index to guarantee idempotency within the database.
- The deduplication window is obtained by sorting by descending `captured_at` and taking N records.
- History is not purged as part of this feature.
- Unmodeled provider fields remain in `raw_json`.

## Configuration

| Field | Type | Required | Rules |
|---|---|---:|---|
| `kexp_plays_url` | URL | yes | URL of the play collection |
| `fetch_limit` | positive integer | yes | M, maximum number of plays to consider |
| `deduplication_window` | positive integer | yes | N, number of recent songs to compare |
| `database_path` | path | yes | SQLite path |
| `request_timeout_seconds` | positive number | yes | Total or base HTTP client timeout |
| `config_file` | path | yes | YAML file that must always exist and be loaded |
| `log_file_path` | path | no | Rotating log file; defaults to `data/kexp2spotify.log` |
| `log_level` | enum | no | One of `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`; defaults to `INFO` |
| `log_file_max_bytes` | positive integer | no | Maximum size before rotation; defaults to 10 MiB |
| `log_file_backup_count` | non-negative integer | no | Number of rotated files to retain; defaults to 5 |
| `log_console` | boolean | no | Whether to also emit logs to stderr; defaults to `true` |

Environment variables use the configured prefix and override YAML values after source merging. Exact names and nesting belong to the implementation contract and must be documented in the example configuration.

The logging environment overrides are `KEXP2SPOTIFY_LOG_FILE_PATH`, `KEXP2SPOTIFY_LOG_LEVEL`, `KEXP2SPOTIFY_LOG_FILE_MAX_BYTES`, `KEXP2SPOTIFY_LOG_FILE_BACKUP_COUNT`, and `KEXP2SPOTIFY_LOG_CONSOLE`.

## Operational logging

Each record includes a local timestamp in ISO-style form, level, logger name, and diagnostic message. File output uses size-based rotation and does not include credentials, tokens, authorization headers, or complete provider payloads.

## State Flow

`received` → `validated_trackplay` → `deduplication_candidate` → `persisted`.

Invalid or non-`trackplay` items end in `discarded`; network, schema, configuration, or persistence failures end the execution without committing the current batch.
