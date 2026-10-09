# Contract: Spotify Login and Update Commands

## Login command

An explicit interactive command/script is allowed and expected for initial setup and reauthorization.

```text
kexp2spotify spotify-login --config /absolute/path/config.yml
```

Behavior:

1. Validate Client ID, redirect URI, scopes, and token path.
2. Generate a cryptographically random PKCE verifier/challenge and state value.
3. If browser opening is enabled and possible, open Spotify authorization; otherwise print the complete one-time authorization URL and wait for the operator to open it elsewhere.
4. Listen only on the configured loopback callback so an SSH local-port forward can deliver the callback from the operator’s browser.
5. Validate returned state, exchange the code, and atomically persist the refresh token.
6. Print a success message without printing tokens or secrets.

The command is interactive and must not be used by cron.

### SSH mode

On the remote host, select a fixed registered callback port and run the login command in a terminal. From the operator workstation, forward that same local port to the remote host:

```sh
ssh -N -L PORT:127.0.0.1:PORT user@remote-host
```

Open the printed Spotify authorization URL in the operator workstation’s browser. Spotify redirects to `http://127.0.0.1:PORT/callback`; the SSH tunnel forwards that request to the waiting remote CLI. The login command must not require a graphical session or a local browser on the remote host.

The implementation must not claim to support a fully browserless user authorization flow unless Spotify adds a documented device authorization flow.

## Scheduled update command

```text
kexp2spotify spotify-update --config /absolute/path/config.yml
```

Behavior:

- Never opens a browser.
- Loads the persisted authorization, refreshing the access token as needed.
- Returns exit code `0` for completed synchronization, including no eligible changes.
- Returns a distinct non-zero result/diagnostic for reauthorization required, configuration failure, provider failure, or partial synchronization.
- Logs counts and affected show IDs, but never secrets, authorization codes, or token payloads.

## Configuration contract

The following names are supported by YAML and environment overrides. Exact environment precedence follows the existing project convention.

```ini
SPOTIFY_CLIENT_ID=[Spotify API Client ID]
SPOTIFY_CLIENT_SECRET=[optional; unused by PKCE and never required for the default CLI flow]
SPOTIFY_SCOPE='playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private ugc-image-upload'
SPOTIFY_REDIRECT_URI='http://127.0.0.1:PORT/callback'
SPOTIFY_TOKEN_PATH=/absolute/path/to/spotify-token.json
SPOTIFY_PLAYLIST_LIMIT=50
SPOTIFY_TIMEZONE=Europe/Madrid
```

`http://localhost` is not a valid default redirect URI. The URI must be registered in the Spotify Developer Dashboard and must match the configured callback rules.
