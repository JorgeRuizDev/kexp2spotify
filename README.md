 # KEXP2Spotify

KEXP play collector with a Spotify destination. The crawler stores validated `trackplay` records in SQLite; an explicit login authorizes Spotify once, while scheduled updates reuse the saved refresh token without opening a browser.

## Run

Install the package and development extras with `uv`, copy `config.example.yml` to a mandatory YAML configuration file, and optionally create a `.env` file in the current working directory for environment overrides. Then run:

```sh
uv sync --extra dev
uv run python main.py --config /absolute/path/to/config.yml
```

The CLI loads `.env` automatically when present. Explicitly exported environment variables take precedence over `.env`, and both take precedence over YAML values.

The same command is suitable for cron. Use absolute paths for the config and database, and redirect stdout/stderr for monitoring. Environment variables named `KEXP2SPOTIFY_<FIELD>` override YAML values, for example `KEXP2SPOTIFY_FETCH_LIMIT`.

The process exits `0` for a completed run (including no new records) and `1` for configuration, source, or persistence failures. Logs contain phase and summary counts but never the full provider payload.

## Spotify

Copy the Spotify fields from [config.example.yml](config.example.yml) into the YAML file or use the `SPOTIFY_*` environment overrides. The Client ID and loopback redirect URI are required for Spotify commands; the Client Secret is optional for PKCE. Store the token outside the repository.

Run the interactive flow once:

```sh
uv run kexp2spotify spotify-login --config /absolute/path/to/config.yml
```

Run the unattended operation from cron or Task Scheduler:

```sh
uv run kexp2spotify spotify-update --config /absolute/path/to/config.yml
```

See [docs/spotify-login.md](docs/spotify-login.md) for SSH port forwarding, permissions, reauthorization, and official Spotify references.

See [the feature quickstart](specs/001-kexp-play-crawler/quickstart.md) for validation scenarios and troubleshooting guidance.

## Quality checks

Run the quality checks through the project environment:

```sh
uv run pytest -q
uv run mypy
uv run ruff check .
```

## Troubleshooting

Ensure the YAML file exists and contains all six fields, the database parent directory is writable, and the KEXP endpoint is reachable. A malformed response or HTTP timeout leaves the current batch uncommitted; retrying the same run is safe.
