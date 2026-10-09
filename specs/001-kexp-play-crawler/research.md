# Research: KEXP Play Crawler

## Decision: Standard Python with typed adapters and `httpx` for HTTP

**Rationale**: The project already requires Python >=3.11 and the crawler is a small batch process. `httpx` provides a reusable client, explicit timeouts, and a differentiated hierarchy for network and HTTP-response errors. The implementation will configure connection, read, write, and pool timeouts instead of allowing an indefinite wait.

**Alternatives considered**: `urllib.request` reduces dependencies but makes testing and fine-grained timeout control less convenient; `requests` is valid but offers no necessary advantage for this design.

**Sources**: [HTTPX timeouts](https://www.python-httpx.org/advanced/timeouts/), [HTTPX exceptions](https://www.python-httpx.org/exceptions/).

## Decision: `pydantic-settings` with `YamlConfigSettingsSource` and environment variables taking precedence over YAML

**Rationale**: The user requires YAML to always be loaded and environment variables to be able to override it. `pydantic-settings` provides a YAML source and allows source ordering to be customized; the design will use a required `YamlConfigSettingsSource` followed by `EnvSettingsSource`, giving environment variables higher priority. `PyYAML` will be included through the YAML extra. Models will validate URLs, positive integers, timeouts, and paths before opening the source or database.

**Alternatives considered**: Reading YAML with PyYAML and applying `os.environ` manually would duplicate precedence and validation rules; a `.env` file does not satisfy the mandatory YAML requirement.

**Sources**: [Pydantic Settings: sources and precedence](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/), [`YamlConfigSettingsSource`](https://github.com/pydantic/pydantic-settings/blob/main/pydantic_settings/sources/providers/yaml.py), [pydantic-settings YAML extra](https://github.com/pydantic/pydantic-settings/blob/main/pyproject.toml).

## Decision: SQLite with `sqlite3` and one transaction per run

**Rationale**: SQLite is explicitly required and the standard library avoids an unnecessary ORM. A song table with a unique index on `track_id`, queries ordered by ingestion timestamp to obtain the latest N records, and a transaction for batch insertion will be used. The external query and validation happen before the transaction begins, so failures do not leave partial inserts.

**Alternatives considered**: SQLAlchemy adds useful abstraction for larger applications, but is unnecessary for a local one-table process; an in-memory database does not work for successive runs.

## Decision: Paginate only when the provider response requires it

**Rationale**: The M limit is configurable and the client must honor it. The adapter will interpret KEXP's documented collection shape, retain only the required items, and follow pagination links/parameters only until it gathers M items or exhausts the results. A malformed response fails explicitly.

**Alternatives considered**: Downloading a large fixed number wastes network capacity and breaks the configurable contract; assuming a single JSON shape would make the adapter fragile.

## Decision: CLI with exit codes and simple structured logs

**Rationale**: The cron job needs to distinguish success with no changes, success with insertions, and failure. The CLI entry point will load configuration, run the use case, and emit a summary of received/filtered/duplicate/inserted items. Errors will not include secrets or the complete JSON in logs by default.

**Alternatives considered**: Not returning an exit code makes cron alerts harder; a web API is out of scope.
