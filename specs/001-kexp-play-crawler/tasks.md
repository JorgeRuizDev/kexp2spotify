---

description: "Task list for implementing the KEXP Play Crawler"
---

# Tasks: KEXP Play Crawler

**Input**: Design documents from `/specs/001-kexp-play-crawler/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: Included because the project constitution requires unit, contract, and integration tests for domain rules, external adapters, and persistence changes.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize the Python package, dependencies, quality tools, and test layout.

- [X] T001 Update `pyproject.toml` with runtime dependencies `pydantic`, `pydantic-settings[yaml]`, and `httpx`, plus development dependencies `pytest`, `pytest-httpx`, `mypy`, `ruff`, and `types-PyYAML`
- [X] T002 [P] Create the package and test directories `src/kexp2spotify/`, `tests/unit/`, `tests/contract/`, and `tests/integration/`, including required `__init__.py` files
- [X] T003 [P] Configure `pytest`, `mypy`, and `ruff` settings in `pyproject.toml` for Python 3.11+, `src/`, and `tests/`
- [X] T004 [P] Add `config.example.yml` with crawler and logging settings, including `log_file_path`, `log_level`, rotation limits, and `log_console`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish typed ports, domain models, configuration loading, and SQLite schema required by all stories.

**⚠️ CRITICAL**: User story work depends on this phase.

- [X] T005 Create typed domain models and validation helpers in `src/kexp2spotify/domain.py`, enforcing `play_type == "trackplay"`, non-empty `track_id`, required non-empty `song` and `artist`, nullable `album` and `release_date`, UTC `captured_at`, and preservation of provider fields in `raw_json`
- [X] T006 [P] Define source and repository protocols in `src/kexp2spotify/ports.py` so the domain depends only on typed abstractions, not HTTPX, KEXP JSON, or `sqlite3`
- [X] T007 Implement mandatory YAML loading, environment-variable precedence, and typed validation in `src/kexp2spotify/config.py` using `pydantic-settings`; reject missing/unreadable/invalid YAML and invalid positive limits, timeout, URL, or database path before side effects
- [X] T008 [P] Add configuration unit tests in `tests/unit/test_config.py` covering YAML loading, environment overrides, precedence, missing YAML, malformed YAML, and invalid values
- [X] T009 Implement SQLite schema initialization and connection lifecycle in `src/kexp2spotify/sqlite_repository.py`, including a unique `track_id`, fields from `data-model.md`, serialized `raw_json`, and indexes needed for newest-by-`captured_at` queries
- [X] T010 [P] Add repository schema/invariant integration tests in `tests/integration/test_sqlite_repository.py`, including unique `track_id`, nullable metadata, raw JSON round-trip, and transaction rollback
- [X] T011 Create typed application errors and safe logging setup in `src/kexp2spotify/errors.py` and `src/kexp2spotify/logging.py`, including timestamped rotating file output, configurable level/path/console behavior, and no secrets or full raw payloads

**Checkpoint**: Configuration, domain contracts, and a transactional SQLite foundation are ready.

---

## Phase 3: User Story 1 - Collect newly aired songs (Priority: P1) 🎯 MVP

**Goal**: Fetch recent KEXP plays, keep only valid `trackplay` items, and persist new songs for the next pipeline step.

**Independent Test**: With an empty temporary SQLite database and a controlled KEXP collection containing trackplay and non-trackplay objects, execute one collection cycle and verify that only valid songs are persisted with normalized fields and complete raw JSON.

### Tests for User Story 1

- [X] T012 [P] [US1] Add KEXP source contract fixtures in `tests/contract/fixtures/kexp_plays.json` covering valid trackplays, non-trackplay objects, optional fields, and provider collection metadata
- [X] T013 [P] [US1] Add HTTP contract tests in `tests/contract/test_kexp_client.py` for configured GET URL, fetch limit M, successful collection parsing, empty results, malformed collection, non-2xx response, and timeout
- [X] T014 [P] [US1] Add ingestion integration tests in `tests/integration/test_crawler_ingestion.py` verifying valid trackplay persistence, complete `raw_json`, captured timestamp, and zero-change behavior for no eligible songs

### Implementation for User Story 1

- [X] T015 [US1] Implement the KEXP HTTP adapter in `src/kexp2spotify/kexp_client.py`, using configured URL, M limit, explicit HTTPX timeouts, typed transport/status errors, collection-shape validation, and safe extraction of play objects without applying trackplay fields to other play types
- [X] T016 [US1] Implement `insert_many` and pipeline-read methods in `src/kexp2spotify/sqlite_repository.py`, persisting name, artist, album, release date, play identifier, `track_id`, UTC `captured_at`, `play_type`, and full `raw_json` in one transaction
- [X] T017 [US1] Implement the first collection use case in `src/kexp2spotify/crawler.py`, orchestrating source retrieval, trackplay/domain validation, candidate mapping, transactional persistence, and received/eligible/discarded/inserted counts
- [X] T018 [US1] Implement the non-interactive entry point in `src/kexp2spotify/cli.py` and delegate `main.py` to it, loading the mandatory YAML configuration before creating source or repository adapters

**Checkpoint**: US1 runs one complete collection cycle and provides persisted songs to downstream readers.

---

## Phase 4: User Story 2 - Avoid duplicates across runs (Priority: P1)

**Goal**: Compare incoming `track_id` values with the N most recently stored songs and avoid duplicates within and across executions while retaining all history.

**Independent Test**: Seed more than N records, return known and new track IDs including duplicate IDs in the same response, and verify that only candidates not present in the recent N-window are inserted once; older historical records remain stored.

### Tests for User Story 2

- [X] T019 [P] [US2] Add domain deduplication unit tests in `tests/unit/test_deduplication.py` for recent-window membership, repeated incoming `track_id`, fewer-than-N stored records, and exact `track_id` identity
- [X] T020 [P] [US2] Add deduplication integration tests in `tests/integration/test_crawler_deduplication.py` for known recent songs, new songs, songs outside the N-window, and historical retention

### Implementation for User Story 2

- [X] T021 [US2] Implement a repository query in `src/kexp2spotify/sqlite_repository.py` that returns the N most recent `track_id` values ordered by `captured_at` descending with deterministic tie-breaking
- [X] T022 [US2] Implement deduplication and within-batch uniqueness in `src/kexp2spotify/crawler.py`, using only `track_id`, comparing against the configured N-window, and retaining all existing historical rows
- [X] T023 [US2] Make batch insertion idempotent in `src/kexp2spotify/sqlite_repository.py` and map duplicate conflicts to duplicate counts without aborting valid new inserts
- [X] T024 [US2] Extend `tests/integration/test_crawler_ingestion.py` with repeated-execution assertions proving that processing the same response twice inserts zero additional rows

**Checkpoint**: US1 and US2 work independently after foundation and repeated cron executions do not create recent duplicates.

---

## Phase 5: User Story 3 - Resume safely after failures (Priority: P2)

**Goal**: Make source, validation, and persistence failures observable and safe to retry without corrupting confirmed data or committing a partial batch.

**Independent Test**: Simulate source timeout, malformed individual items, and a persistence failure; verify non-zero failure signaling, diagnostic summaries, preservation of pre-existing rows, and safe retry behavior.

### Tests for User Story 3

- [X] T025 [P] [US3] Add failure-path unit tests in `tests/unit/test_errors_and_logging.py` for typed configuration/source/persistence errors, safe messages, and summary counts
- [X] T026 [P] [US3] Add failure-path integration tests in `tests/integration/test_failure_recovery.py` for HTTP failure, malformed items, transaction rollback, no partial batch commit, and retry without duplicate rows
- [X] T027 [P] [US3] Add CLI contract tests in `tests/contract/test_cli.py` for exit code 0 on no-op/success, non-zero exit on configuration/source/persistence failure, and summary output fields

### Implementation for User Story 3

- [X] T028 [US3] Add atomic batch behavior and rollback-safe error mapping in `src/kexp2spotify/sqlite_repository.py`, preserving rows committed by prior executions while rejecting the current failed batch
- [X] T029 [US3] Add malformed-item isolation and phase-specific error handling in `src/kexp2spotify/crawler.py`, skipping invalid individual plays while failing the whole run for invalid collection responses or source errors
- [X] T030 [US3] Complete cron-oriented CLI behavior in `src/kexp2spotify/cli.py`, including exit codes, safe summary logging, absolute/configurable path support, and no interactive prompts
- [X] T031 [US3] Add a documented cron invocation and operational troubleshooting section to `README.md`, referencing `specs/001-kexp-play-crawler/quickstart.md`

**Checkpoint**: Failed runs are diagnosable, leave no partial current batch, and can be retried safely.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Verify the complete design, quality gates, and operational quickstart.

- [X] T032 [P] Add public API/type documentation and module docstrings across `src/kexp2spotify/`
- [X] T033 [P] Add static quality checks and type annotations for all public functions in `src/kexp2spotify/`, then resolve `ruff` and `mypy` findings
- [X] T034 Run the end-to-end scenarios from `specs/001-kexp-play-crawler/quickstart.md` using temporary YAML, HTTP fixtures, and SQLite paths
- [X] T035 Run the full test suite and quality commands from `pyproject.toml`, recording any environment-specific limitations in `README.md`
- [X] T036 Review implementation against `spec.md`, `plan.md`, `data-model.md`, and `contracts/`, and update documentation for any intentional deviations

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies.
- **Phase 2 (Foundational)**: Depends on Phase 1 and blocks all user story phases.
- **Phase 3 (US1)**: Depends on Phase 2; delivers the MVP.
- **Phase 4 (US2)**: Depends on Phase 2 and integrates with the US1 crawler/repository paths; can begin after the shared foundation, but its final verification depends on the ingestion flow from US1.
- **Phase 5 (US3)**: Depends on the US1 and US2 execution paths being present.
- **Phase 6 (Polish)**: Depends on all desired stories.

### User Story Dependencies

- **US1 (P1)**: No user-story dependency; requires Phase 2.
- **US2 (P1)**: Requires Phase 2 and reuses the domain/repository/crawler seams established by US1.
- **US3 (P2)**: Requires the complete US1/US2 execution path to verify retry and rollback behavior.

### Parallel Opportunities

- T002, T003, and T004 can run in parallel after T001.
- T006, T008, T009, and T011 can run in parallel after the package exists; T010 follows T009.
- Within US1, T012, T013, and T014 can run in parallel before T015–T018.
- Within US2, T019 and T020 can run in parallel; T021 can proceed independently from the tests.
- Within US3, T025, T026, and T027 can run in parallel before implementation refinements.
- T032 and T033 can run in parallel with documentation-oriented T034 after feature code stabilizes.

## Parallel Example: User Story 1

```text
Developer A: T012 + T013 — source fixtures and KEXP contract tests
Developer B: T014 — ingestion integration tests
After the tests are ready:
Developer A: T015 — KEXP HTTP adapter
Developer B: T016 — SQLite insertion/read methods
Developer C: T017 + T018 — orchestration and CLI wiring
```

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1 and Phase 2.
2. Complete Phase 3 (US1).
3. Run the independent US1 test and quickstart scenarios.
4. Stop for validation: the crawler can fetch and persist new trackplays, but deduplication and failure hardening are not yet complete.

### Incremental Delivery

1. Add US2 to make repeated cron executions idempotent and history-preserving.
2. Add US3 to make failures transactional, retryable, and monitorable.
3. Complete Phase 6 and re-run all quickstart scenarios.

## Notes

- Every task uses the required checklist format and includes a concrete file path.
- `track_id` is the only deduplication identity; `id` is retained as the provider play identifier.
- The YAML file is mandatory on every run; environment variables override YAML values.
- The feature does not include Spotify playlist updates.
