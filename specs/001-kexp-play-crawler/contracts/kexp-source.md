# KEXP Source Contract

## Request

- Method: `GET`
- URL: configured `kexp_plays_url`; default example is `https://api.kexp.org/v2/plays/`
- Limit: configured `fetch_limit` (M), applied through the provider's supported query/pagination mechanism
- Timeout: configured request timeout; no unbounded network wait

## Accepted response

The adapter accepts the provider's collection response and extracts individual play objects. A play is eligible when `play_type == "trackplay"`, `song` and `artist` are valid, and it has a usable identity. Prefer non-empty `track_id`; when absent, use non-empty `recording_id`; when both are absent, use the play `id`.

The adapter preserves the full original play object as `raw_json`. It must not assume non-trackplay objects have the same fields.

## Failure contract

- Network timeout/transport failure: typed source error; no persistence.
- Non-success HTTP status: typed source error; no persistence.
- Invalid JSON or unsupported collection shape: typed source error; no persistence.
- Malformed individual item: skip item, count it in the execution summary, and continue when the collection itself is valid.

## Test double

Contract tests must cover a valid collection, a mixed collection, empty results, malformed collection, non-2xx response, timeout, and pagination/limit behavior.
