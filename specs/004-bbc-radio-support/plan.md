# Implementation Plan: BBC Radio Support

**Branch**: `004-bbc-radio-support` | **Date**: 2026-10-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/004-bbc-radio-support/spec.md`

## Summary

Add BBC Sounds recent music plays to the existing `spotify-update` command. A fixed catalog of nine music radio services defines the exact BBC service IDs, display names, formats, and optional station-logo URLs. Each service is fetched and normalized independently; its plays are grouped into one Spotify playlist named for that station, regardless of programme. BBC playlists reuse the existing Spotify authorization, track resolver, playlist limit, and timezone-aware update description. The existing KEXP show playlists and KEXP Latest Tracks playlist remain intact.

The BBC Radio and Music Services (RMS) endpoint used by BBC Sounds was observed returning recent segment metadata without a caller API key. BBC does not document this endpoint as a supported external API, so access is public in observed behavior but comes with no stability or availability contract. The adapter will isolate this integration behind a typed source port, explicit timeout and response validation, fixture-backed contract tests, and per-station retries. No BBC credentials or API-key configuration will be introduced.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: Existing `httpx`, Pydantic, SQLite, Spotify Web API client, Pillow; no new runtime dependency planned.

**Storage**: Existing SQLite `songs` table. BBC segment event keys will be source-qualified in `track_id`; station identity and original BBC payload will be retained in `raw_json`. This avoids a schema migration while preserving existing KEXP rows and uniqueness constraints.

**Testing**: Existing pytest unit, HTTP contract, and integration test layout; run project lint and strict typing gates for the implementation.

**Target Platform**: Existing Python CLI/cron runtime.

**Project Type**: Single Python package and CLI.

**Performance Goals**: Fetch at most configured `fetch_limit` records per service per run. Sequential service requests avoid adding load or concurrency complexity; service failures must not prevent later work.

**Constraints**: Use one request timeout from current settings; retry each KEXP/BBC source unit independently using the current bounded retry policy. Spotify configuration/authorization is a run-wide preflight. Per-service fetch, validation, track lookup, playlist, and artwork errors are captured and processing continues with the remaining stations and KEXP. Report a partial run as failed and return nonzero after all units have been attempted. Failures in global configuration, Spotify authorization, or required shared persistence remain fatal. Do not claim exact wall-clock airtimes when RMS provides only relative ordering/offset metadata.

**Scale/Scope**: Nine BBC services plus the existing KEXP source in one `spotify-update`; no BBC local/national spoken-word or sports services and no BBC aggregate playlist.

## Constitution Check

| Gate | Status | Design response |
|---|---|---|
| SOLID responsibilities | Pass | Service catalog, RMS HTTP adapter, normalization, collection, playlist synchronization, and CLI orchestration remain separate responsibilities. |
| Static typing | Pass | New ports, normalized records, per-unit outcomes, and adapter methods use explicit types and strict type checking. |
| Provider-agnostic boundaries | Pass with one documented integration limitation | BBC RMS payloads stay inside the BBC adapter; domain records carry normalized fields and opaque source-qualified event identity. The RMS endpoint is an observed public HTTP interface but is not officially documented for external developers. The adapter contract and fixtures will document observed behavior and surface schema changes; upstream stability cannot be guaranteed. This narrow exception is required by the user's request to use the BBC public API. |
| Spec Kit context | Pass | `.specify/memory/context.md` was read before this plan step. |
| Resilience, timeout, retries, observability | Pass | Explicit timeout, bounded per-unit retries, station-scoped errors and aggregate partial-failure exit status; no secrets in logs. |
| Test gates | Pass | Unit tests for service filtering, normalization/order and aggregation; contract tests for each supported response shape; integration tests for mixed success/failure, persistence and Spotify queue behavior. |

**Post-design re-check**: No additional architecture or dependency is introduced. The only constrained exception remains the BBC endpoint's lack of an official external API support contract, documented above and in [research.md](research.md).

## Project Structure

### Documentation (this feature)

```text
specs/004-bbc-radio-support/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── bbc-rms.openapi.yaml
│   └── station-catalog.schema.json
└── tasks.md                 # Generated by $speckit-tasks
```

### Source Code (repository root)

```text
src/kexp2spotify/
├── bbc_catalog.py           # Fixed nine-station catalog and supported-service lookup
├── bbc_client.py            # RMS HTTP adapter, response validation, and normalization
├── bbc_sync.py              # Per-station grouping and Spotify reconciliation
├── cli.py                   # Combined, failure-isolated spotify-update orchestration
├── crawler.py               # Shared collection/deduplication use case (extend only if needed)
├── domain.py                # Provider-neutral play/order fields if needed by normalization
├── ports.py                 # Typed BBC source and repository contracts
├── spotify_playlists.py     # Reusable queue reconciliation; station names remain unprefixed
├── spotify_sync.py          # Existing KEXP synchronization, unchanged in behavior
└── sqlite_repository.py     # Existing persistence, no migration expected

tests/
├── contract/
│   ├── fixtures/bbc_rms_latest.json
│   └── test_bbc_client.py
├── integration/
│   ├── test_bbc_ingestion.py
│   ├── test_bbc_spotify_workflow.py
│   └── test_spotify_workflow.py   # Existing KEXP regression coverage
└── unit/
    ├── test_bbc_catalog.py
    ├── test_bbc_normalization.py
    └── test_partial_update.py
```

**Structure Decision**: Extend the existing single Python project. BBC-specific transport and orchestration live in focused modules, while shared collection, persistence, Spotify destination behavior, and KEXP synchronization continue to use the existing contracts. `bbc_sync` will call shared playlist reconciliation with the exact BBC station name (no `KEXP - ` prefix) and a source-qualified managed identity.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Reliance on an undocumented upstream RMS endpoint | The user's requested public BBC metadata source is accessible without a key in observed calls; BBC does not publish an external support contract for it. | Requiring BBC credentials would not match the observed public endpoint or user requirement. The risk is contained in one adapter and checked by contract fixtures. |

