# Research: Spotify Show Playlists

**Date**: 2026-10-10

## Decision: Authorization Code with PKCE for the one-time login command

**Rationale**: The application modifies playlists belonging to a Spotify user, so client credentials are insufficient. PKCE allows the unmanaged CLI to avoid treating a distributed client secret as confidential while still receiving refreshable user authorization. The login command can open the user’s browser, run a short-lived local callback listener, exchange the code, and persist the resulting refresh token.

**Alternatives considered**:

- Client credentials: rejected because it cannot access or modify user playlists.
- Authorization Code with a client secret: viable for a confidential server, but unsuitable as the default for a local/unmanaged CLI because the secret cannot be protected on the operator’s machine.
- Implicit grant: rejected because it is deprecated and does not provide the required refresh behavior.

**Sources**: [Spotify authorization](https://developer.spotify.com/documentation/web-api/concepts/authorization), [PKCE flow](https://developer.spotify.com/documentation/web-api/tutorials/code-pkce-flow).

## Decision: Registered loopback callback on an explicit IP

**Rationale**: The login helper needs a callback that works on the operator’s machine without a public web service. Spotify’s redirect URI rules require HTTPS except for loopback IPs; `localhost` is not used. Register `http://127.0.0.1:<port>/callback` according to the provider’s current loopback rules and keep the listener alive only for the authorization transaction.

**Alternatives considered**:

- `http://localhost`: rejected because it is not an accepted redirect form under the current rules.
- Public HTTPS callback service: unnecessary operational surface for a single unmanaged CLI.
- Manual copy/paste of the authorization code: less convenient and more error-prone than a loopback callback.

**Source**: [Spotify redirect URI rules](https://developer.spotify.com/documentation/web-api/concepts/redirect_uri).

## Decision: Scope set includes playlist read/modify and artwork upload

**Rationale**: The adapter must find the managed playlist, create or edit public/private playlists, and upload the show picture. The default requested scopes are:

```text
playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private ugc-image-upload
```

The operator may use a narrower set only when the configured playlist visibility and discovery strategy make that safe. `SPOTIFY_SCOPE` remains configurable, but missing scopes produce an actionable preflight error.

**Alternatives considered**:

- The user-provided three playlist scopes only: insufficient for custom cover upload and private-playlist discovery.
- Request every Spotify scope: rejected because least privilege is safer and makes consent clearer.

**Sources**: [Spotify scopes](https://developer.spotify.com/documentation/web-api/concepts/scopes), [create playlist](https://developer.spotify.com/documentation/web-api/reference/create-playlist), [custom playlist cover](https://developer.spotify.com/documentation/web-api/reference/upload-custom-playlist-cover).

## Decision: Refresh access tokens, but plan periodic interactive reauthorization

**Rationale**: Access tokens are short-lived, so scheduled runs refresh them from the persisted refresh token. The current Spotify guidance indicates Developer Dashboard refresh tokens can expire after six months and refreshing does not extend that deadline. The CLI must surface a re-login command and a clear scheduler diagnostic instead of looping or modifying playlists without authorization. If Spotify returns a replacement refresh token, atomically replace the stored token; otherwise retain the current one.

**Alternatives considered**:

- Assume refresh tokens are indefinite: rejected because it would make unattended failure surprising and undocumented.
- Store only access tokens: rejected because scheduled runs would require interactive login roughly hourly.

**Source**: [Spotify refreshing tokens](https://developer.spotify.com/documentation/web-api/tutorials/refreshing-tokens).

## Decision: Current playlist item contract stays inside the adapter

**Rationale**: Spotify’s current documentation distinguishes the current playlist item endpoints from deprecated track endpoints. The adapter owns endpoint paths, pagination, snapshot/version information, URI serialization, and provider errors. Domain code sees ordered destination track identifiers and reconciliation results only.

**Source**: [Spotify authorization documentation](https://developer.spotify.com/documentation/web-api/concepts/authorization).

## Decision: Secure local token storage is an explicit operational requirement

**Rationale**: The token is equivalent to long-lived access to the configured Spotify account. The token file must have restrictive permissions where supported, be excluded from version control, never be printed, and be written atomically. The documentation will tell operators where it is stored and how to remove it to force a fresh login.

**Alternatives considered**:

- Environment variable only: workable for deployment but inconvenient for a one-time browser flow and easy to expose in process inspection.
- SQLite token storage: rejected because credential lifecycle should not be coupled to the song database.
