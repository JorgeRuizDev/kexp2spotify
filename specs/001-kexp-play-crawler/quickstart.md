# Quickstart: KEXP Play Crawler

## Prerequisites

- Python 3.11 or newer.
- Project dependencies installed.
- Network access to the configured KEXP URL.
- A YAML configuration file.

## Example configuration

Create `config.example.yml` in the repository root and copy it to the path used by the run. The implementation must document the exact environment-variable prefix and names.

```yaml
kexp_plays_url: "https://api.kexp.org/v2/plays/"
fetch_limit: 50
deduplication_window: 100
database_path: "data/kexp.sqlite3"
request_timeout_seconds: 10
config_file: "config.yml"
log_file_path: "data/kexp2spotify.log"
log_level: "INFO"
log_file_max_bytes: 10485760
log_file_backup_count: 5
log_console: true
```

## Validation scenarios

1. **First run**: use an empty SQLite path and a fixture response containing `trackplay` and non-trackplay objects. Run the CLI and verify that only valid tracks are inserted and the raw JSON is preserved.
2. **Idempotent run**: run again against the same fixture and verify that zero new records are inserted.
3. **Environment override**: set the environment variable for `fetch_limit` to a value different from YAML; verify that the effective run uses the environment value.
4. **Invalid YAML**: remove or corrupt the mandatory YAML file; verify a non-zero exit code and no database changes.
5. **Provider failure**: make the HTTP adapter return a timeout or non-2xx response; verify a non-zero exit code and no partial batch commit.
6. **Window behavior**: prefill more than N records, return one `track_id` in the recent window and one outside it, and verify only the expected candidate is inserted according to the configured N-window rule.
7. **End-to-end**: run against a controlled HTTP fixture and a temporary SQLite database, then query persisted fields and `raw_json` as the next pipeline step would.
8. **Logging**: set `log_file_path` to a temporary nested path, run the CLI, and verify that the file is created with timestamped records. Set `KEXP2SPOTIFY_LOG_LEVEL=DEBUG` and verify that the environment override takes precedence over YAML.

## Cron validation

Invoke the same non-interactive CLI command from cron with an absolute config path and a working directory-independent SQLite path. Verify that stdout/stderr and the process exit code are sufficient for cron monitoring.
