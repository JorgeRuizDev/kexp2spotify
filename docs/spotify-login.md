# Spotify login and unattended playlist updates

This project uses Spotify user authorization to create and update playlists. The normal scheduled update is non-interactive. You perform a browser login once—locally or through an SSH session with the browser on another machine—then the CLI reuses the saved authorization until Spotify requires you to authorize again.

## 1. Create the Spotify application

1. Open the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).
2. Create an application and copy its **Client ID**.
3. Register a loopback redirect URI using an explicit IP, such as:

   ```text
   http://127.0.0.1:PORT/callback
   ```

   Replace `PORT` with the port configured for this project. Do not use `http://localhost`; Spotify’s current redirect rules require an explicit loopback IP for HTTP callbacks. The URI used by the CLI must match the registered value and configuration.

The CLI uses Authorization Code with PKCE. A Client Secret is not required for the default unmanaged CLI flow because a secret stored on an operator’s machine cannot be treated as confidential. If your environment provides `SPOTIFY_CLIENT_SECRET` for compatibility, keep it private; the login flow must never print or commit it.

## 2. Configure the project

Put the values in the project’s YAML configuration or provide the corresponding environment overrides. Never commit real credentials or the token file.

```ini
SPOTIFY_CLIENT_ID=[your Spotify API Client ID]
SPOTIFY_CLIENT_SECRET=[optional; not required by PKCE]
SPOTIFY_SCOPE='playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private ugc-image-upload'
SPOTIFY_REDIRECT_URI='http://127.0.0.1:PORT/callback'
SPOTIFY_TOKEN_PATH=/absolute/path/to/spotify-token.json
SPOTIFY_PLAYLIST_LIMIT=50
SPOTIFY_TIMEZONE=Europe/Madrid
```

The scopes mean:

- `playlist-read-private`: find and inspect private managed playlists.
- `playlist-read-collaborative`: include collaborative playlists when discovery requires it.
- `playlist-modify-public`: create/update public playlists.
- `playlist-modify-private`: create/update private playlists.
- `ugc-image-upload`: upload the show picture as the playlist cover.

Request only the scopes your configured visibility and discovery behavior require, but removing a required scope causes a clear preflight failure rather than a partial update.

## 3. Log in once

Run the explicit interactive login command:

```sh
kexp2spotify spotify-login --config /absolute/path/to/config.yml
```

The command generates a PKCE challenge, prints the consent URL, optionally opens it, receives the callback on the loopback listener, exchanges the authorization code, and stores the refresh token at `SPOTIFY_TOKEN_PATH`. Do not paste the token into a ticket, shell history, log, or configuration committed to Git.

### Login through SSH

A browser is not required on the remote server. Spotify still requires the operator to authenticate on its consent page, so open the printed URL in a browser on your workstation.

1. Register a fixed callback such as `http://127.0.0.1:8765/callback` and configure the same port in the remote job.
2. On your workstation, create the tunnel before completing consent:

   ```sh
   ssh -N -L 8765:127.0.0.1:8765 user@remote-host
   ```

3. In a second SSH session, run `kexp2spotify spotify-login --config /absolute/path/to/config.yml` on the remote host.
4. Open the printed Spotify URL in your workstation browser and approve access.
5. Spotify redirects to `http://127.0.0.1:8765/callback`; the tunnel delivers it to the remote CLI, which saves the token.

The login command must not depend on a GUI, `DISPLAY`, or browser executable on the remote host. Spotify does not document a device-code flow for this Web API authorization, so completely browserless user login is not part of the plan.

After a successful login, run a normal update once to verify access:

```sh
kexp2spotify spotify-update --config /absolute/path/to/config.yml
```

## 4. Run unattended updates

The scheduled update command does not open a browser. It loads the saved refresh token, obtains a short-lived access token when needed, and synchronizes the show playlists. The token file must remain readable by the same OS user that runs the scheduler.

Use an absolute configuration and token path in cron, Task Scheduler, or another job runner. Keep scheduler output available for diagnostics, but never enable logging that includes environment variables or HTTP authorization headers.

## 5. Log in again when required

If Spotify reports an invalid, revoked, or expired refresh token, the update exits with a reauthorization diagnostic and does not modify playlists. Run the login command again interactively:

```sh
kexp2spotify spotify-login --config /absolute/path/to/config.yml
```

Spotify access tokens are short-lived, and current Developer Dashboard refresh-token rules may require reauthorization after approximately six months. Refreshing an access token does not guarantee that the refresh token’s lifetime is extended. Plan a periodic manual check of the scheduler and repeat login before the authorization becomes unusable.

If you intentionally want to force a new consent flow, stop the scheduler, remove the token file at `SPOTIFY_TOKEN_PATH`, and run `spotify-login` again. Only remove the exact configured token file; do not delete the whole configuration or database directory.

## Official references

- [Authorization concepts](https://developer.spotify.com/documentation/web-api/concepts/authorization)
- [Authorization Code with PKCE](https://developer.spotify.com/documentation/web-api/tutorials/code-pkce-flow)
- [Redirect URI rules](https://developer.spotify.com/documentation/web-api/concepts/redirect_uri)
- [Scopes](https://developer.spotify.com/documentation/web-api/concepts/scopes)
- [Refreshing tokens](https://developer.spotify.com/documentation/web-api/tutorials/refreshing-tokens)
- [Create a playlist](https://developer.spotify.com/documentation/web-api/reference/create-playlist)
- [Upload a custom playlist cover](https://developer.spotify.com/documentation/web-api/reference/upload-custom-playlist-cover)
