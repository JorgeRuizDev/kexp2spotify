---

description: "Implementation tasks for Spotify show playlists"
---

# Tasks: Spotify Show Playlists

**Input**: Design documents from `/specs/002-spotify-playlists/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, and `quickstart.md`

**Tests**: Included because the project constitution requires proportional unit, contract, and integration coverage for domain and provider changes.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish configuration, dependency, and repository safeguards for Spotify work.

- [X] T001 Add Spotify runtime configuration fields, YAML examples, and environment override names in `src/kexp2spotify/config.py` and `config.example.yml`, including `SPOTIFY_CLIENT_ID`, optional `SPOTIFY_CLIENT_SECRET`, `SPOTIFY_SCOPE`, `SPOTIFY_REDIRECT_URI`, `SPOTIFY_TOKEN_PATH`, `SPOTIFY_PLAYLIST_LIMIT`, and `SPOTIFY_TIMEZONE`.
- [X] T002 [P] Add the Spotify token file, credential patterns, and local authorization artifacts to `.gitignore`.
- [X] T003 [P] Add or confirm the HTTP and test dependencies required by the typed Spotify adapter in `pyproject.toml` without introducing an unneeded OAuth framework.
- [X] T004 [P] Add shared Spotify error categories and redaction helpers in `src/kexp2spotify/errors.py` and `src/kexp2spotify/logging.py`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the typed boundaries and security primitives required by every user story.

**⚠️ CRITICAL**: No user story implementation can begin until this phase is complete.

- [X] T005 Define typed Show, SongQueueItem, ManagedPlaylist, AuthorizationState, and SynchronizationResult models in `src/kexp2spotify/domain.py`, preserving the constraints from `specs/002-spotify-playlists/data-model.md` including non-empty stable IDs/names, timezone-aware queue timestamps, unique playlist association, and bounded track lists.
- [X] T006 [P] Extend provider-neutral ports for authorization, playlist discovery/mutation, token storage, and destination reconciliation in `src/kexp2spotify/ports.py` based on `specs/002-spotify-playlists/contracts/spotify-destination.md` and `spotify-login-cli.md`.
- [X] T007 [P] Add unit tests for model validation, description formatting inputs, secret redaction, and invalid configuration cases in `tests/unit/test_spotify_models.py` and `tests/unit/test_spotify_config.py`.
- [X] T008 Implement atomic token-file persistence with restrictive permissions, replacement-token handling, missing/corrupt-file diagnostics, and no secret logging in `src/kexp2spotify/spotify_token_store.py`.
- [X] T009 [P] Add token-store tests covering atomic writes, reloads, replacement refresh tokens, corrupt files, and permission intent in `tests/integration/test_spotify_token_store.py`.
- [X] T010 Define typed HTTP transport behavior for timeouts, JSON errors, 401/403/404/409/429 responses, retry-after handling, and redacted diagnostics in `src/kexp2spotify/spotify_http.py`.
- [X] T011 [P] Add provider-response fixtures and transport contract tests in `tests/contract/fixtures/spotify/` and `tests/contract/test_spotify_http.py`.

**Checkpoint**: Typed domain, configuration, token storage, and HTTP error foundations are ready; user stories can proceed in priority order.

---

## Phase 3: User Story 1 - Authorize Spotify for unattended use (Priority: P1) 🎯 MVP

**Goal**: Complete an explicit login over a local terminal or SSH session, persist a refresh token securely, and refresh access without a browser during scheduled runs.

**Independent Test**: Run login with a mocked authorization callback, verify a token is stored without appearing in output, run a scheduled refresh without a browser, and verify invalid authorization stops before playlist mutation.

### Tests for User Story 1

- [X] T012 [P] [US1] Add PKCE verifier/challenge, state validation, authorization URL, callback, and token-exchange contract fixtures in `tests/contract/fixtures/spotify_auth/` and `tests/contract/test_spotify_auth.py`.
- [X] T013 [P] [US1] Add SSH-mode integration tests proving the login command prints the URL, binds the configured loopback port, accepts the forwarded callback, and never requires `DISPLAY` or a browser executable in `tests/integration/test_spotify_login_ssh.py`.
- [X] T014 [P] [US1] Add scheduled refresh tests for access-token expiry, replacement refresh tokens, `invalid_grant`, missing scopes, and redacted errors in `tests/unit/test_spotify_auth.py`.

### Implementation for User Story 1

- [X] T015 [US1] Implement PKCE verifier/challenge generation, state generation/validation, authorization URL construction, callback parsing, and code exchange in `src/kexp2spotify/spotify_auth.py` using the configured Client ID and redirect URI.
- [X] T016 [US1] Implement the SSH-safe login listener in `src/kexp2spotify/spotify_auth.py` so browser auto-open is optional, the complete consent URL is printed, the callback listens on the loopback address, and the command works without GUI environment variables.
- [X] T017 [US1] Implement access-token refresh and reauthorization-required error mapping in `src/kexp2spotify/spotify_auth.py`, retaining the existing refresh token when Spotify does not return a replacement and atomically replacing it when one is returned.
- [X] T018 [US1] Add `spotify-login` and authorization preflight handling to `src/kexp2spotify/cli.py`, including safe success output and distinct non-zero behavior for missing credentials, callback failure, invalid scopes, and `invalid_grant`.
- [X] T019 [US1] Add the non-interactive authorization loader/refresh path used by scheduled work in `src/kexp2spotify/spotify_auth.py` and expose it through the typed port without opening a browser.

**Checkpoint**: User Story 1 is independently functional; an operator can authorize through SSH with a browser on another machine and scheduled runs can refresh tokens without a browser.

---

## Phase 4: User Story 2 - Maintain one playlist for each show (Priority: P1)

**Goal**: Create or find exactly one managed playlist per stable show and keep shows isolated.

**Independent Test**: Synchronize songs for two stable show IDs against mocked Spotify responses and verify one correctly named playlist per show with no cross-show tracks.

### Tests for User Story 2

- [X] T020 [P] [US2] Add Spotify playlist discovery/create/details contract tests for stable show association, exact `KEXP - <show name>` naming, pagination, and ambiguous matches in `tests/contract/test_spotify_playlists.py`.
- [X] T021 [P] [US2] Add multi-show reconciliation integration tests proving playlist isolation and retry-safe reuse in `tests/integration/test_spotify_playlist_reconciliation.py`.

### Implementation for User Story 2

- [X] T022 [US2] Implement typed Spotify Web API playlist discovery, creation, metadata updates, pagination, and provider error mapping in `src/kexp2spotify/spotify_client.py` using current playlist item/detail operations.
- [X] T023 [US2] Implement stable show-to-playlist reconciliation and exact playlist-name normalization in `src/kexp2spotify/spotify_playlists.py`, rejecting empty show names and reporting ambiguous candidates deterministically.
- [X] T024 [US2] Add show/song destination mapping from the existing crawler output into provider-neutral playlist input in `src/kexp2spotify/spotify_playlists.py` and `src/kexp2spotify/domain.py` without leaking Spotify response models into the domain.
- [X] T025 [US2] Add `spotify-update` CLI orchestration in `src/kexp2spotify/cli.py`, validating configuration and authorization before any playlist mutation and returning cron-friendly result codes.

**Checkpoint**: User Story 2 is independently functional; each stable show has one isolated managed playlist and repeated runs reuse it.

---

## Phase 5: User Story 3 - Enforce a bounded FIFO playlist queue (Priority: P1)

**Goal**: Reconcile songs in chronological queue order, avoid duplicates, and remove the oldest items first to enforce the configured positive limit.

**Independent Test**: Feed a show queue larger than the configured limit, synchronize twice, and verify exact newest-item retention, oldest-first removal, and no duplicates.

### Tests for User Story 3

- [X] T026 [P] [US3] Add unit tests for chronological ordering, duplicate preservation, limit-one behavior, invalid zero/negative limits, and deterministic tie-breaking in `tests/unit/test_spotify_queue.py`.
- [X] T027 [P] [US3] Add provider contract tests for append/remove batches, item positions, snapshots, pagination, and retry-safe reconciliation in `tests/contract/test_spotify_queue_client.py`.
- [X] T028 [P] [US3] Add end-to-end reconciliation tests for unchanged input, over-limit input, unresolved tracks, and interrupted mutation retry in `tests/integration/test_spotify_fifo.py`.

### Implementation for User Story 3

- [X] T029 [US3] Implement provider-neutral FIFO queue reconciliation in `src/kexp2spotify/spotify_playlists.py`, preserving existing item positions for duplicates, appending new items chronologically, and removing oldest items until the positive configured limit is satisfied.
- [X] T030 [US3] Implement Spotify track resolution and current playlist item append/remove batching in `src/kexp2spotify/spotify_client.py`, mapping unresolved tracks and provider snapshots into typed results.
- [X] T031 [US3] Add idempotent retry behavior and partial-failure reporting in `src/kexp2spotify/spotify_playlists.py`, re-reading managed playlist state before retrying mutations and never creating duplicate playlists or items.

**Checkpoint**: User Story 3 is independently functional; FIFO behavior is deterministic, bounded, duplicate-safe, and retry-safe.

---

## Phase 6: User Story 4 - Present show artwork and synchronization status (Priority: P2)

**Goal**: Apply the show picture and exact last-updated description without preventing song synchronization when artwork is unavailable.

**Independent Test**: Synchronize a show with an image at a known timezone/time, verify the cover and exact description, then repeat with an unavailable image and verify the playlist still updates.

### Tests for User Story 4

- [X] T032 [P] [US4] Add unit tests for exact `Last Updated at HH:MM at DD-MM-YYYY (Timezone) + Autogenerated by https://github.com/JorgeRuizDev/kexp2spotify` formatting across midnight and daylight-saving transitions in `tests/unit/test_spotify_description.py`.
- [X] T033 [P] [US4] Add cover-upload contract tests for JPEG size/type validation, successful upload, provider rejection, and preservation fallback in `tests/contract/test_spotify_cover.py`.
- [X] T034 [P] [US4] Add integration tests proving description update, successful artwork update, unavailable-artwork continuation, and diagnostic reporting in `tests/integration/test_spotify_metadata.py`.

### Implementation for User Story 4

- [X] T035 [US4] Implement timezone-aware exact playlist-description generation in `src/kexp2spotify/spotify_playlists.py`, validating the configured IANA timezone before mutation.
- [X] T036 [US4] Implement show-picture preparation and Spotify custom-cover upload in `src/kexp2spotify/spotify_client.py`, enforcing provider image requirements and returning `updated`, `preserved`, or `unavailable` outcomes.
- [X] T037 [US4] Integrate description and cover outcomes into playlist reconciliation and structured CLI logging in `src/kexp2spotify/spotify_playlists.py` and `src/kexp2spotify/cli.py` without logging credentials or token material.

**Checkpoint**: User Story 4 is independently functional; every successful update has the required description and available show artwork, while unavailable artwork remains non-fatal.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Complete operator documentation, harden deployment behavior, and validate the whole feature.

- [X] T038 [P] Update `docs/spotify-login.md` with the final command names, actual configuration keys, SSH `ssh -L` example, token-file permissions, reauthorization procedure, and official Spotify links.
- [X] T039 [P] Update `README.md` and `config.example.yml` to describe Spotify setup, the separation between interactive login and scheduled update, and the fact that the Client Secret is optional for PKCE.
- [X] T040 [P] Add a scheduler-safe integration test and example invocation for absolute config/token paths in `tests/integration/test_spotify_cli.py`.
- [X] T041 Run the scenarios in `specs/002-spotify-playlists/quickstart.md` with mocked provider responses and record any deviations in that file.
- [X] T042 Run `python -m pytest -q`, `python -m mypy`, and `python -m ruff check .`; fix failures in the affected source/test files and verify no secrets appear in logs or tracked files.
- [X] T043 Review the final implementation against `.specify/memory/constitution.md`, `specs/002-spotify-playlists/spec.md`, and all contract documents; update `specs/002-spotify-playlists/checklists/requirements.md` only if requirements changed.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; T001-T004 can run in parallel where files do not overlap.
- **Foundational (Phase 2)**: Depends on Setup; T005-T011 block every user story.
- **User Story 1 (Phase 3)**: Depends on Foundational; is the MVP and enables authenticated provider calls.
- **User Story 2 (Phase 4)**: Depends on Foundational and the authorization boundary from US1; establishes playlist identity and provider reconciliation.
- **User Story 3 (Phase 5)**: Depends on US2 playlist discovery/mutation; adds queue reconciliation.
- **User Story 4 (Phase 6)**: Depends on US2 and the mutation boundary from US3; adds metadata and artwork.
- **Polish (Phase 7)**: Depends on the desired user stories being complete.

### User Story Dependencies

- **US1 (P1)**: No story dependency after Foundational; can be delivered as the MVP.
- **US2 (P1)**: Requires US1’s authorization contract but can use mocked authorization in its isolated tests.
- **US3 (P1)**: Requires US2’s managed-playlist identity and provider mutation operations.
- **US4 (P2)**: Requires US2’s playlist metadata boundary and US3’s reconciliation lifecycle.

### Parallel Opportunities

- T002-T004 can run in parallel after confirming the existing config/error conventions.
- T006-T007, T009, and T011 can run in parallel after the shared domain direction is agreed.
- T012-T014 can run in parallel before US1 implementation.
- T020-T021 can run in parallel before US2 implementation.
- T026-T028 can run in parallel before US3 implementation.
- T032-T034 can run in parallel before US4 implementation.
- T038-T040 can run in parallel during Polish.

## Parallel Example: User Story 1

```text
Task T012: Contract fixtures and tests for PKCE/callback/token exchange
Task T013: SSH-mode callback integration tests
Task T014: Refresh and invalid_grant unit tests
```

## Parallel Example: User Story 3

```text
Task T026: FIFO domain unit tests
Task T027: Spotify append/remove contract tests
Task T028: Retry and over-limit integration tests
```

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2.
2. Complete User Story 1, including SSH login and secure token persistence.
3. Validate login and refresh independently with mocked Spotify responses.
4. Add the minimum US2 playlist discovery/create path needed to demonstrate one show playlist.

### Incremental Delivery

1. Add US2 playlist-per-show synchronization.
2. Add US3 FIFO reconciliation and retry safety.
3. Add US4 artwork and exact description metadata.
4. Finish operator docs, scheduler validation, and full quality gates.

### Notes

- Every task uses the required checkbox/ID/optional-parallel/story-label format.
- `[P]` is used only where tasks have disjoint files or independent test scopes.
- Provider credentials, authorization codes, refresh tokens, and HTTP authorization headers must never appear in tests, fixtures, logs, or committed configuration.
