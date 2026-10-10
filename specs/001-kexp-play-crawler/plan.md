# Implementation Plan: KEXP Play Crawler

**Branch**: `001-kexp-play-crawler` | **Date**: 2026-10-09 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-kexp-play-crawler/spec.md`

## Summary

Build a cron-executable crawler that queries recent KEXP plays, filters exclusively for `trackplay`, deduplicates by `track_id` (falling back to `recording_id`, then play `id`) against the latest N songs, and persists new songs with their metadata and original JSON in SQLite. Configuration will always be loaded from YAML and combined with higher-precedence environment variables through `pydantic-settings`. The process also writes timestamped, safe, rotating operational logs with configurable file path, level, retention, and console output. The design separates configuration, the HTTP adapter, the song domain, the deduplication use case, and the SQLite repository.

## Technical Context

**Language/Version**: Python >=3.11 (already fixed in `pyproject.toml`)

**Primary Dependencies**: `pydantic`/`pydantic-settings` with YAML support, `PyYAML`, `httpx`, `pytest`, `pytest-httpx`, `mypy`, and `ruff`

**Storage**: SQLite through the standard-library `sqlite3`; complete JSON serialized in a text column

**Testing**: `pytest` for unit and integration tests; HTTP doubles for the KEXP contract; `mypy` and `ruff` as static checks

**Target Platform**: Non-interactive Python process on a Linux server invoked by cron

**Project Type**: CLI/proceso batch interno

**Performance Goals**: Process up to M plays and finish in under 60 seconds under normal conditions; one query per run unless the response requires pagination

**Constraints**: Mandatory YAML; environment variables override YAML; do not modify SQLite if the query or response validation fails; configurable URLs, M, N, timeout, SQLite path, and logging destination/level/rotation

**Scale/Scope**: One station, periodic runs, local SQLite, growing historical volume, and responses bounded by M; no web API or Spotify integration in this feature

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

*GATE: PASS*

- **SOLID and clear responsibilities**: configuration, KEXP source, domain, use case, and persistence are designed as replaceable components.
- **Static typing**: all public interfaces and models will have annotations; the plan includes `mypy`.
- **Source/destination agnostic**: KEXP and SQLite will sit behind ports/adapters; the domain will not depend on their JSON or `sqlite3`.
- **Testable integrations**: the HTTP adapter will have timeouts, typed errors, an M limit, and contract tests with an HTTP double.
- **Proportional testing**: unit tests for deduplication/configuration, contract tests for KEXP, and integration tests for SQLite and the complete flow.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file ($speckit-plan command output)
├── research.md          # Phase 0 output ($speckit-plan command)
├── data-model.md        # Phase 1 output ($speckit-plan command)
├── quickstart.md        # Phase 1 output ($speckit-plan command)
├── contracts/           # Phase 1 output ($speckit-plan command)
└── tasks.md             # Phase 2 output ($speckit-tasks command - NOT created by $speckit-plan)
```

### Source Code (repository root)
-->

```text
src/
└── kexp2spotify/
    ├── config.py          # YAML + environment, typed validation
    ├── domain.py          # models and rules without external dependencies
    ├── ports.py           # source and repository contracts
    ├── kexp_client.py     # KEXP HTTP adapter
    ├── sqlite_repository.py
    ├── crawler.py         # use case/orchestration
    └── cli.py             # cron entry point and exit codes

tests/
├── unit/
├── contract/
└── integration/

config.example.yml
```

**Structure Decision**: Single Python project with a package under `src/`, explicit source and storage ports, separate concrete adapters, and tests organized by contract type. `main.py` may delegate to `kexp2spotify.cli` during implementation to preserve a simple entry point.

## Constitution Check — Post-Design

*GATE: PASS*

- The domain model and ports do not depend on KEXP, SQLite, HTTPX, or the external JSON format.
- Configuration is isolated in a typed model and validated before creating external effects.
- The KEXP adapter encapsulates URL, limits, pagination, timeouts, HTTP responses, and errors.
- The SQLite repository encapsulates schema, unique index, N window, and batch transaction.
- Planned tests cover the domain, configuration, HTTP contract, persistence, and complete execution.
- No violations of SOLID, static typing, source/destination agnosticism, or quality gates were detected.

## Complexity Tracking

There are no constitutional violations requiring justification.
