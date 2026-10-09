# Implementation Plan: Spotify Show Playlists

**Branch**: `002-spotify-playlists` | **Date**: 2026-10-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-spotify-playlists/spec.md`

## Summary

Add a Spotify destination adapter to the existing typed, provider-agnostic pipeline. The adapter will maintain one playlist per stable show, apply the configured FIFO limit, synchronize cover art and the required description, and expose a separate one-time login command for interactive authorization. Scheduled playlist updates will reuse a securely persisted refresh token and will not open a browser. The project will document setup and reauthorization under `docs/`.

The chosen authorization design is OAuth Authorization Code with PKCE. It requires a Spotify Client ID but does not require storing a Client Secret in this unmanaged CLI. The login command must support both optional local browser opening and SSH/headless operation: it prints the authorization URL, listens on the remote loopback callback, and allows the operator to open the URL on another machine through an SSH local-port forward. Access tokens will be refreshed during scheduled runs; the operator will be prompted to repeat login when Spotify invalidates or expires the persisted refresh token.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: Existing `pydantic`, `pydantic-settings`, `httpx`; standard-library PKCE, local callback, and secure token-file support unless the implementation selects a narrowly scoped compatible helper.

**Storage**: Existing SQLite database for songs; a separate local authorization/token file with restrictive permissions. No client secrets or refresh tokens in SQLite, logs, or source control.

**Testing**: Existing pytest, pytest-httpx, mypy strict, and ruff configuration. Add unit tests for FIFO and description rules, contract tests for the Spotify adapter and token responses, and integration tests for the CLI/configuration boundary.

**Target Platform**: Python CLI on the operator’s workstation or an unattended Linux/Windows host; explicit login may run over SSH with the browser on a separate workstation.

**Project Type**: Command-line application with source and destination adapters.

**Performance Goals**: A normal scheduled run should complete within 60 seconds for the configured show/song batch, excluding provider backoff; pagination and batching must avoid unnecessary provider requests.

**Constraints**: Spotify user authorization is required; client-credentials authentication cannot modify user playlists. Spotify does not provide a documented device-code flow for this use case, so SSH login still requires the operator to open the printed consent URL in a browser on another machine. The redirect URI must use HTTPS or an explicitly registered loopback IP; `localhost` is not used. The persisted refresh token may require a fresh login after the provider’s current lifetime policy. Provider rate limits and 429 responses must be handled without unsafe duplicate writes.

**Scale/Scope**: One managed Spotify account, up to the project’s configured shows and playlist limit, one local authorization identity, and repeated cron-style executions. Multi-user account management, web dashboards, and arbitrary playlist administration are out of scope.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **SOLID responsibilities**: PASS. Domain queue rules, authorization, Spotify HTTP behavior, persistence, and CLI orchestration are separate responsibilities behind typed ports.
- **Static typing**: PASS. New production interfaces and models are typed; strict mypy remains a quality gate.
- **Provider/source agnosticism**: PASS. Spotify-specific authentication, serialization, pagination, rate limits, and errors remain in an adapter. The core receives show and song contracts rather than Spotify models.
- **Standard integration contracts**: PASS. The destination adapter uses the provider’s documented Web API; no browser automation is used for normal updates.
- **Security and observability**: PASS with design constraint. Tokens and credentials are redacted and stored outside logs; timeouts, retry rules, and provider error context are explicit.
- **Testing**: PASS. Unit, contract, and integration coverage is planned for changed domain and provider boundaries.

## Project Structure

### Documentation (this feature)

```text
specs/002-spotify-playlists/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── spotify-destination.md
│   └── spotify-login-cli.md
└── tasks.md                 # Created by $speckit-tasks
```

### Source Code (repository root)

```text
src/kexp2spotify/
├── domain.py                 # Existing song model; add show/queue value objects only if needed
├── ports.py                  # Add typed destination and authorization ports
├── spotify_auth.py           # PKCE login, callback, token refresh, secure token persistence
├── spotify_client.py         # Typed Spotify Web API adapter and provider error mapping
├── spotify_playlists.py      # Playlist reconciliation orchestration
├── config.py                 # Spotify settings and environment/YAML validation
├── cli.py                    # Existing crawl command plus explicit spotify-login/update commands
└── errors.py

tests/
├── unit/
│   ├── test_spotify_queue.py
│   ├── test_spotify_description.py
│   └── test_spotify_auth.py
├── contract/
│   ├── test_spotify_client.py
│   └── fixtures/
└── integration/
    ├── test_spotify_cli.py
    └── test_spotify_token_store.py

docs/
└── spotify-login.md
```

**Structure Decision**: Extend the existing single Python CLI project. Spotify-specific code is split between authentication, provider transport, and playlist reconciliation so the domain remains source/destination agnostic and each boundary can be tested independently.

## Phase 0: Research Decisions

Research is recorded in [research.md](research.md). The key decisions are:

1. Use Authorization Code with PKCE for the explicit login command; do not depend on a client secret for the unmanaged CLI.
2. Use an explicitly registered loopback redirect such as `http://127.0.0.1:<port>/callback`; do not use `http://localhost`.
3. Request the playlist read/modify scopes needed by the selected playlist visibility plus `ugc-image-upload` for show artwork. The default scope set is documented in `docs/spotify-login.md` and remains configurable.
4. Persist and rotate refresh tokens securely; treat `invalid_grant` and equivalent authorization failures as a re-login requirement.
5. Support SSH login by printing the consent URL and documenting `ssh -L` port forwarding; browser auto-open is only a convenience.
6. Use current playlist item operations and provider IDs inside the adapter; do not expose provider payloads to the domain.

## Phase 1: Design Outputs

- [data-model.md](data-model.md) defines shows, queue items, managed playlists, authorization state, and synchronization results.
- [contracts/spotify-destination.md](contracts/spotify-destination.md) defines the typed destination boundary and reconciliation behavior.
- [contracts/spotify-login-cli.md](contracts/spotify-login-cli.md) defines the explicit login command and non-interactive update command expectations.
- [quickstart.md](quickstart.md) defines local setup, login, dry-run/test validation, and unattended execution checks.
- [../../docs/spotify-login.md](../../docs/spotify-login.md) is the operator-facing setup and reauthorization guide requested for this feature.

## Complexity Tracking

No constitution violations require an exception. The separate login command is an intentional boundary between interactive setup and unattended operation, permitted by the feature specification.
