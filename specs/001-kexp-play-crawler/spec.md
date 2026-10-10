# Feature Specification: KEXP Play Crawler

**Feature Branch**: `001-kexp-play-crawler`

**Created**: 2026-10-09

**Status**: Draft

**Input**: User description: "Implement a simple crawler that queries the latest KEXP songs, discards those already known within the latest N songs, stores new ones in SQLite, and makes them available to the next pipeline step, initially executed through cron."

## Clarifications

### Session 2026-10-09

- Q: Which identifier should determine whether a song is already stored: `track_id`, the play identifier (`id`), or a combination of fields? → A: Prefer `track_id`; if KEXP omits it, use `recording_id`, then the play identifier (`id`) as a last resort.
- Q: Should the database retain the complete history of captured songs or remove songs that fall outside the latest N? → A: Retain the complete history; N only limits deduplication.
- Additional input: Limits, KEXP URLs, and the remaining operational parameters must be configured through a YAML file that is always loaded; environment variables may override its values, using typed configuration based on `pydantic-settings`.

### Session 2026-10-10

- Additional input: The process MUST write timestamped operational logs to a configurable file. The log path, level, rotation limits, and console output MUST be configurable through YAML and overridable with `KEXP2SPOTIFY_*` environment variables.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Collect newly aired songs (Priority: P1)

As a pipeline operator, I want to run a periodic collection of the latest songs aired by KEXP so that new songs are available to later steps.

**Why this priority**: This is the primary goal of the feature and provides the data input required by the entire pipeline.

**Independent Test**: Given a known response from the KEXP service and an empty database, run a collection and verify that only valid song-type items are stored.

**Acceptance Scenarios**:

1. **Given** a valid response with songs and other play types, **When** collection runs, **Then** only items whose `play_type` is `trackplay` are considered and stored.
2. **Given** a valid response with new songs, **When** collection finishes, **Then** each new song is persisted with its main data and complete JSON for the next pipeline step.
3. **Given** a scheduled run with no new songs, **When** collection finishes, **Then** the run completes successfully without creating duplicates.

### User Story 2 - Avoid duplicates across runs (Priority: P1)

As a pipeline operator, I want each run to compare retrieved songs with the latest songs already stored so that the same song is not processed repeatedly.

**Why this priority**: Runs are periodic; without deduplication, storage and later steps would receive repeated data.

**Independent Test**: Prepopulate the database with a window of known songs, return a mixture of known and new songs, and verify that only new songs within the configured window are inserted.

**Acceptance Scenarios**:

1. **Given** a song whose identifier is among the latest N stored songs, **When** the response is processed, **Then** another copy is not inserted.
2. **Given** a song whose identifier is not among the latest N stored songs, **When** the response is processed, **Then** it is inserted as a new song.
3. **Given** a response containing the same identifier more than once, **When** it is processed, **Then** it is stored only once.

### User Story 3 - Resume safely after failures (Priority: P2)

As a cron operator, I want network or data failures not to corrupt already stored information or turn a partial run into duplicates.

**Why this priority**: Unattended runs must be diagnosable and repeatable without frequent manual intervention.

**Independent Test**: Simulate a service error and a response with invalid records, and verify that previously persisted data remains intact and that the run reports the failure.

**Acceptance Scenarios**:

1. **Given** that the external service does not respond correctly, **When** collection runs, **Then** existing records are not modified and the result indicates the error.
2. **Given** items missing the fields required to represent a song, **When** the response is processed, **Then** those items are skipped and the remaining valid songs are preserved.
3. **Given** that the process runs again after a failure, **When** it receives the same data, **Then** it does not create duplicates of records that were already confirmed.

### Edge Cases

- The response is empty or contains no `trackplay` items.
- The response has an unexpected structure or cannot be interpreted as a collection of plays.
- A song lacks one or more optional values, such as album or release date; it must be retained with those fields empty, without inventing values.
- A song lacks an identifier or the minimum data needed to identify it; it must be omitted and recorded as unprocessable.
- The same song appears multiple times in the current response.
- The database already contains fewer than N songs.
- Two collections run very close together.
- The service returns more items than the requested or configured M limit.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST query the KEXP play source and request the latest M plays, where M is configurable.
- **FR-002**: The system MUST consider only plays whose `play_type` is exactly `trackplay`.
- **FR-003**: The system MUST identify and deduplicate a song by `track_id` when present, otherwise by `recording_id`, and otherwise by the play identifier (`id`); it MUST reject items with none of these identifiers.
- **FR-004**: The system MUST compare received songs with the identifiers of the latest N stored songs, where N is configurable.
- **FR-005**: The system MUST insert only songs not present in that N-song window and MUST prevent duplicates within a single run.
- **FR-006**: The system MUST persist, at minimum, the song name, artist, album, release date, identifier, ingestion timestamp, and complete play JSON.
- **FR-007**: The system MUST retain absent optional fields as empty or null values, without replacing them with invented information.
- **FR-008**: The system MUST store records in a local SQLite database reusable across runs.
- **FR-009**: The system MUST make newly inserted songs queryable by the next pipeline step, including their complete JSON.
- **FR-010**: The system MUST treat a response with no new songs as a valid run with no database changes.
- **FR-011**: The system MUST report query, invalid-response, and persistence errors with enough detail to diagnose the cron job.
- **FR-012**: The system MUST preserve records confirmed before a failure and allow the run to be repeated without duplicating them.
- **FR-013**: The system MUST support non-interactive execution and configuration suitable for invocation by cron.
- **FR-014**: The system MUST keep play retrieval, deduplication, and persistence separate so each responsibility can be tested independently.
- **FR-015**: The system MUST load a YAML configuration file on every run; a missing, inaccessible, or invalid file MUST prevent execution and produce a clear diagnostic.
- **FR-016**: The system MUST allow YAML configuration of, at minimum, the KEXP source URL, M play limit, N deduplication limit, and database path.
- **FR-017**: The system MUST allow environment variables to override YAML values, deterministically giving environment variables precedence over the file.
- **FR-018**: Configuration MUST be validated through a typed model based on `pydantic-settings`, and missing, invalid, or incompatible values MUST produce an error before querying the source or modifying the database.
- **FR-019**: The system MUST write operational logs to `data/kexp2spotify.log` by default, with an ISO-style timestamp on every record.
- **FR-020**: The system MUST allow YAML configuration of `log_file_path`, `log_level`, `log_file_max_bytes`, `log_file_backup_count`, and `log_console`.
- **FR-021**: The system MUST allow each logging configuration field to be overridden by its corresponding `KEXP2SPOTIFY_<FIELD>` environment variable, while keeping secrets and full provider payloads out of logs.

### Key Entities

- **Play**: An item received from the external source; it contains the play type, identifiers, musical metadata, and original JSON.
- **Stored song**: A persisted representation of a valid `trackplay`, with normalized data, ingestion timestamp, and complete JSON.
- **Deduplication window**: The N most recently stored songs against which new plays are compared.
- **Collection run**: One crawler invocation with M and N parameters, result, errors, and counts of received, discarded, and inserted items.
- **Operational log**: A timestamped diagnostic record written to the configured rotating log file and, when enabled, to the console.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: During a normal run, at least 100% of valid plays with `play_type=trackplay` that are not in the configured window become available to the next pipeline step.
- **SC-002**: In a repeated run with the same response, the number of new records inserted after the first run is 0.
- **SC-003**: A scheduled run processes a response of up to M items and persists the result in under 60 seconds under normal network and local-storage conditions.
- **SC-004**: When the external service fails, 100% of records confirmed before the failure remain recoverable and the run leaves an actionable diagnostic.
- **SC-005**: For every stored song, the operator can verify the name, artist, album, release date, identifier, ingestion timestamp, and original JSON without querying the external source again.
- **SC-006**: An operator can configure the log destination and verbosity through YAML or environment variables and find timestamped records for completed and failed runs in the configured file.

## Assumptions

- The external source provides an orderable collection of recent plays and allows requesting or limiting the number of M results.
- The primary deduplication identifier is `track_id`; `recording_id` is the fallback song identity and the play identifier (`id`) is the final fallback when KEXP omits both. Preserve the full provider payload in `raw_json`.
- M and N have configurable values with reasonable defaults for periodic execution; an administration interface is outside this feature's scope.
- The YAML configuration is always loaded and environment variables act as overrides to simplify cron deployment.
- Configuration is implemented using `pydantic-settings` or the project's equivalent mechanism for combining and validating YAML and environment variables.
- The YAML file path may be defined through an environment variable or the project's documented default.
- SQLite is located at a configurable path accessible to the user running the cron job.
- The database retains the complete history of captured songs; N only limits the deduplication window and does not imply purging old records.
- Authentication is not required to query the specified source.
- The next pipeline step reads songs from the database; Spotify or another destination integration is outside this feature.
