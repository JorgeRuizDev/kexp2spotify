---

description: "Dependency-ordered implementation tasks for BBC Radio support"
---

# Tasks: BBC Radio Support

**Input**: Design documents from `/specs/004-bbc-radio-support/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, and `quickstart.md`

**Tests**: Included because the plan and project constitution specify unit, HTTP contract, and integration coverage for the BBC source and Spotify workflow changes.

**Organization**: Tasks are grouped by user story so station grouping, queue maintenance, and playlist metadata can be delivered and checked as increments.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it uses separate files and has no dependency on an incomplete task
- **[Story]**: User story label; setup and foundational tasks have no story label
- Every task names its implementation or test file path

## Path Conventions

- Python package: `src/kexp2spotify/`
- Tests: `tests/unit/`, `tests/contract/`, and `tests/integration/`
- Feature documentation: `specs/004-bbc-radio-support/`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and dependency setup.

The repository already has the Python package, Spotify configuration, and required runtime dependencies. No setup changes are needed for this feature.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add the typed source and managed-playlist identity boundaries required before BBC story implementation.

- [X] T001 [P] Define a typed BBC latest-segments source port in `src/kexp2spotify/ports.py`, including station-scoped fetch input and normalized play output.
- [X] T002 [P] Extend managed playlist identity markers and discovery in `src/kexp2spotify/spotify_metadata.py` and `src/kexp2spotify/spotify_client.py` to support `bbc:{service_id}` identities while retaining existing KEXP markers and deterministic duplicate reporting.

**Checkpoint**: BBC source and source-qualified playlist identity boundaries are available without changing KEXP identity behavior.

---

## Phase 3: User Story 1 - Follow BBC music radio stations (Priority: P1) 🎯 MVP

**Goal**: Fetch eligible plays from exactly the nine allowlisted music services and group all shows from each service into one station playlist.

**Independent Test**: Feed eligible plays from multiple shows on two supported stations through a mocked source and destination. Verify one correctly named playlist per station, no per-show playlists, no cross-station tracks, and no empty playlist for a station without a resolved track. Verify unsupported services are excluded.

### Tests for User Story 1

- [X] T003 [P] [US1] Add catalog tests for the exact nine service IDs, names, and formats, plus rejection of spoken-word, sports, local, and unknown services, in `tests/unit/test_bbc_catalog.py`.
- [X] T004 [P] [US1] Add the observed latest-segments response fixture in `tests/contract/fixtures/bbc_rms_latest.json` and request/response contract coverage in `tests/contract/test_bbc_client.py` for query parameters, timeout/status handling, and malformed responses.
- [X] T005 [P] [US1] Add normalization tests in `tests/unit/test_bbc_normalization.py` for source-qualified event IDs, title/artist mapping, non-music or malformed segment rejection, captured UTC time, and preservation of relative ordering/offsets without inventing airtimes.
- [X] T006 [P] [US1] Add an ingestion integration test in `tests/integration/test_bbc_ingestion.py` proving station-attributed BBC records persist through the existing SQLite repository without changing KEXP records.

### Implementation for User Story 1

- [X] T007 [P] [US1] Implement the immutable nine-service allowlist and supported-service lookup in `src/kexp2spotify/bbc_catalog.py`, using the exact FR-001 names and formats and optional service-level `logo_url` values.
- [X] T008 [P] [US1] Implement the RMS HTTP adapter and normalization in `src/kexp2spotify/bbc_client.py` using `GET /v2/services/{service_id}/segments/latest`, `experience=domestic`, `offset=0`, `min(fetch_limit, 10)`, and request timeout. Preserve the data-model rules verbatim: `track_id` is `bbc:{service_id}:{segment_id}` and uses `urn` only when `id` is absent; `song` is the non-empty secondary/track title; `artist` is the non-empty primary/artist title; `captured_at` is UTC collection time; `airdate` is unset unless RMS supplies an absolute timezone-aware broadcast timestamp; `play_type` is `trackplay` only for eligible music segments; `raw_json` retains the original fields plus normalized service ID, stable source order, and relative offset/labels; and the existing integer `id` is unset.
- [X] T009 [US1] Implement BBC collection and station-level playlist grouping in `src/kexp2spotify/bbc_sync.py`, assigning service identity from the allowlisted station endpoint, resolving eligible tracks, using the exact catalog station name, and creating no playlist when no eligible track resolves. Never infer station identity from programme metadata.

**Checkpoint**: Eligible tracks from multiple programmes on a supported station produce one station playlist; other stations remain isolated and unsupported services are ignored.

---

## Phase 4: User Story 2 - Keep station playlists current (Priority: P1)

**Goal**: Make BBC playlist updates ordered, unique, bounded, reusable, and safe to retry.

**Independent Test**: Synchronize overlapping plays for one station across repeated runs. Verify unique resolved Spotify URIs, preserved positions for existing tracks, newest-first play ordering, the configured playlist limit, and oldest-first removal when over limit. Simulate one station failure and verify other station and KEXP work continues and the run records a partial failure.

### Tests for User Story 2

- [X] T010 [P] [US2] Add BBC queue unit tests in `tests/unit/test_bbc_queue.py` for stable RMS source order, duplicate URI handling, existing-position preservation, unresolved tracks, positive playlist limits, and oldest-first removal.
- [X] T011 [P] [US2] Add repeated-run and mixed-success integration coverage in `tests/integration/test_bbc_spotify_workflow.py` for playlist reuse, no duplicate playlist/track creation, independent per-station updates, and partial failure reporting.

### Implementation for User Story 2

- [X] T012 [US2] Extend `SongQueueItem` and queue mapping/reconciliation in `src/kexp2spotify/domain.py` and `src/kexp2spotify/spotify_playlists.py` with stable source-order handling for RMS batches whose records share a collection timestamp, preserving current KEXP ordering behavior.
- [X] T013 [US2] Reconcile BBC station queues in `src/kexp2spotify/bbc_sync.py` through the shared queue logic in `src/kexp2spotify/spotify_playlists.py`, de-duplicating by destination URI, preserving an existing occurrence's position, and enforcing `spotify_playlist_limit` independently per station with oldest tracks removed first.
- [X] T014 [US2] Refactor `spotify-update` orchestration in `src/kexp2spotify/cli.py` to validate shared configuration and Spotify authorization once, then retry and report KEXP and each BBC station as independent units. Continue after station-scoped fetch, validation, resolution, playlist, or artwork failures; retain successful updates; preserve existing KEXP show and Latest Tracks behavior; record a partial run as failed; and return nonzero after all units have been attempted.

**Checkpoint**: Repeated unchanged runs add no duplicate tracks or playlists, each station queue stays within the shared configured limit, and an individual station failure does not stop remaining units.

---

## Phase 5: User Story 3 - Recognize and check station playlists (Priority: P2)

**Goal**: Present BBC station identity, available station artwork, and the existing timezone-aware last-updated description.

**Independent Test**: Synchronize a track for a station with a valid logo and inspect its exact playlist name, cover, and update description at a known execution time/timezone. Repeat with unavailable or rejected artwork and verify track synchronization succeeds and existing artwork is preserved when possible.

### Tests for User Story 3

- [X] T015 [P] [US3] Add BBC playlist metadata integration tests in `tests/integration/test_bbc_metadata.py` for exact station names, the existing `Last updated at HH:MM on DD-MM-YYYY (Timezone) ·  github.com/JorgeRuizDev/kexp2spotify` description format, available cover application, and non-fatal missing/rejected artwork.

### Implementation for User Story 3

- [X] T016 [US3] Add validated official service-level logo URLs where available to the catalog entries in `src/kexp2spotify/bbc_catalog.py`; keep unavailable URLs as `None` and never substitute segment artwork for a station logo.
- [X] T017 [US3] Apply optional station artwork and the existing timezone-aware update description during BBC playlist reconciliation in `src/kexp2spotify/bbc_sync.py`, using shared cover preparation and description behavior from `src/kexp2spotify/spotify_playlists.py` so artwork errors do not block track updates.
- [X] T018 [P] [US3] Update `README.md` and `specs/004-bbc-radio-support/quickstart.md` to list all nine supported services, explain station-level grouping across shows, document shared Spotify configuration, affirm existing KEXP playlists continue unchanged, and describe the observed RMS endpoint as undocumented and without an upstream stability guarantee.

**Checkpoint**: Listeners can identify each managed station playlist by name, see the successful update time, and receive station artwork when it is available.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Confirm the planned usage path and repository quality gates after the desired stories are complete.

- [X] T019 Review the completed behavior against `specs/004-bbc-radio-support/quickstart.md`, `.specify/memory/constitution.md`, and `specs/004-bbc-radio-support/contracts/`; update the quickstart or contracts if implementation reveals a documented deviation.

## Operational Follow-up: RMS Page Limit and Retry Classification

- [X] T020 Add contract coverage in `tests/contract/test_bbc_client.py` for the observed RMS maximum page limit of 10 and retry classification for transient and permanent HTTP errors.
- [X] T021 Add CLI retry coverage in `tests/unit/test_bbc_cli.py` proving permanent source errors stop after one attempt and expose a safe diagnostic.
- [X] T022 Cap BBC RMS requests at 10, retry transient 408/425/429/5xx and transport failures, and report the actual attempt count and safe source error detail in `src/kexp2spotify/bbc_client.py`, `src/kexp2spotify/errors.py`, `src/kexp2spotify/observability.py`, and `src/kexp2spotify/cli.py`.
- [X] T023 Document the observed RMS page limit and retry behavior in `specs/004-bbc-radio-support/research.md`, `specs/004-bbc-radio-support/quickstart.md`, and `specs/004-bbc-radio-support/contracts/bbc-rms.openapi.yaml`.
- [X] T024 Include safe `SourceError` messages in per-unit failure logs and summaries so retryable HTTP/status or response-shape failures are diagnosable; cover final retry output in `src/kexp2spotify/cli.py` and `tests/unit/test_bbc_cli.py`.
- [X] T025 Keep the BBC playlist identity suffix inline in the description sent during Spotify playlist creation, and cover the single-line metadata in `src/kexp2spotify/spotify_playlists.py` and `tests/integration/test_bbc_metadata.py`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No changes are needed; the Python project and required dependencies already exist.
- **Foundational (Phase 2)**: T001-T002 establish the typed BBC source and managed-playlist identity boundaries before story work.
- **User Stories (Phase 3+)**: Depend on Phase 2. Implement in priority order because the queue and metadata stories build on station grouping and the BBC sync path.
- **Polish (Phase 6)**: Depends on all desired user stories being complete.

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Phase 2; delivers the MVP station allowlist, source normalization, and station grouping.
- **User Story 2 (P1)**: Depends on User Story 1's normalized station records and grouping path; adds robust queue behavior and combined update orchestration.
- **User Story 3 (P2)**: Depends on User Stories 1 and 2 because artwork and update metadata are applied during station playlist reconciliation.

### Within Each User Story

- Contract, unit, and integration coverage tasks precede implementation tasks and can run in parallel when they use separate files.
- Catalog and RMS adapter work can proceed in parallel after their tests are in place; station synchronization follows both.
- BBC ordering and queue behavior must be implemented before CLI partial-run orchestration is completed.
- Station logo catalog values and README/quickstart updates can proceed independently; BBC metadata reconciliation uses the catalog values.

### Parallel Opportunities

- T001-T002 can run in parallel because they modify separate boundary modules.
- T003-T006 can run in parallel because each uses a separate test or fixture path.
- T007-T008 can run in parallel after the corresponding User Story 1 tests; T009 follows both.
- T010-T011 can run in parallel; T012-T013 follow the queue model and BBC sync dependencies before T014.
- T015 can be prepared independently of T016 and T018; T017 follows the catalog and shared BBC sync implementation.
- T016 and T018 can run in parallel because they modify separate files.

## Parallel Example: User Story 1

```text
Task T003: Add allowlist and exclusion tests in tests/unit/test_bbc_catalog.py
Task T004: Add RMS contract fixture and tests in tests/contract/fixtures/bbc_rms_latest.json and tests/contract/test_bbc_client.py
Task T005: Add normalization tests in tests/unit/test_bbc_normalization.py
Task T006: Add persistence integration coverage in tests/integration/test_bbc_ingestion.py
```

## Parallel Example: User Story 2

```text
Task T010: Add RMS queue-order and limit unit tests in tests/unit/test_bbc_queue.py
Task T011: Add repeated-run and station failure coverage in tests/integration/test_bbc_spotify_workflow.py
```

## Parallel Example: User Story 3

```text
Task T015: Add metadata integration tests in tests/integration/test_bbc_metadata.py
Task T016: Add optional service logo URLs in src/kexp2spotify/bbc_catalog.py
Task T018: Update supported-service and grouping documentation in README.md and specs/004-bbc-radio-support/quickstart.md
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 2: Foundational source and playlist identity boundaries.
2. Complete Phase 3: User Story 1 catalog, RMS adapter, collection, and station grouping.
3. Validate independently with multiple programmes across two supported stations, unsupported service input, and a station with no resolved tracks.
4. The MVP creates correctly grouped station playlists; add queue retry guarantees and metadata polish in the later increments.

### Incremental Delivery

1. Complete User Story 1 and confirm one isolated playlist per supported station with eligible resolved tracks.
2. Add User Story 2 and confirm queue order, limit enforcement, idempotency, and partial-run behavior.
3. Add User Story 3 and confirm logos, update descriptions, and operator documentation.
4. Complete Phase 6 review against the quickstart, constitution, and contracts.

### Notes

- `[P]` marks tasks in separate files with no dependency on incomplete tasks.
- `[US1]`, `[US2]`, and `[US3]` map to the prioritized stories in `specs/004-bbc-radio-support/spec.md`.
- No BBC credentials, new runtime dependencies, schema migration, programme playlists, or aggregate BBC playlist are planned.
