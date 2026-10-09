 # KEXP2Spotify

Non-interactive KEXP play collector. The current feature stores validated `trackplay` records in SQLite; Spotify playlist updates are intentionally outside this scope.

## Run

Install the package and development extras, copy `config.example.yml` to a mandatory YAML configuration file, then run:

```sh
python main.py --config /absolute/path/to/config.yml
```

The same command is suitable for cron. Use absolute paths for the config and database, and redirect stdout/stderr for monitoring. Environment variables named `KEXP2SPOTIFY_<FIELD>` override YAML values, for example `KEXP2SPOTIFY_FETCH_LIMIT`.

The process exits `0` for a completed run (including no new records) and `1` for configuration, source, or persistence failures. Logs contain phase and summary counts but never the full provider payload.

See [the feature quickstart](specs/001-kexp-play-crawler/quickstart.md) for validation scenarios and troubleshooting guidance.

## Quality checks

`python -m pytest -q` passes in the development environment. The current managed environment does not have the optional `ruff` and `mypy` executables installed, so those two configured checks must be run after installing the `dev` extras.

## Troubleshooting

Ensure the YAML file exists and contains all six fields, the database parent directory is writable, and the KEXP endpoint is reachable. A malformed response or HTTP timeout leaves the current batch uncommitted; retrying the same run is safe.
