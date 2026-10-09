# Quickstart: Spotify Show Playlists

This is a validation guide for the planned feature; it is not an implementation recipe.

## Prerequisites

1. A Spotify account permitted to use the project’s Developer Mode application.
2. A Spotify Developer Dashboard application with a registered loopback redirect URI, for example `http://127.0.0.1:PORT/callback`.
3. The project’s existing KEXP YAML configuration and database.
4. A writable token path outside the repository and an environment where the one-time login browser can open.

## Configure credentials

Set the Client ID, redirect URI, token path, scopes, playlist limit, and timezone as described in [the operator login guide](../../docs/spotify-login.md). Treat the Client Secret as unnecessary for the PKCE flow; if supplied for compatibility, never print or commit it.

## Perform one-time login

Run the explicit login command from [contracts/spotify-login-cli.md](contracts/spotify-login-cli.md). Confirm that the browser consent page opens, the loopback callback completes, and the token file is created with restrictive permissions. Confirm that command output contains no token values.

## Validate unattended behavior

1. Run the update command once with a test show/song fixture and verify one playlist named `KEXP - <show name>`.
2. Run it again with unchanged input and verify no duplicate playlist or tracks.
3. Add enough ordered fixture songs to exceed the configured limit and verify oldest-first removal.
4. Verify the cover image and exact generated description.
5. Run the command without a browser and confirm a valid token refresh permits the update.
6. Replace the token with an invalid value and confirm the command exits with a reauthorization diagnostic without modifying playlists.

## Automated checks

Run the project test suite and type/lint checks after installing development dependencies:

```sh
python -m pytest -q
python -m mypy
python -m ruff check .
```

Provider contract tests must use recorded/synthetic responses and must not require a real account or commit credentials.

Validation note: the repository currently has no live Spotify credentials, so the commands are validated with mocked HTTP responses; no real account mutation is performed.
