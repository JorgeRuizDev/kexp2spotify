# CLI Contract

## Invocation

The CLI runs one collection cycle and exits. It must accept a configuration-file path either through the configured environment variable or the documented CLI entry point; the YAML file is always loaded.

## Exit codes

- `0`: collection completed, whether zero or more records were inserted.
- non-zero: configuration, source, schema, or persistence failure.

## Output

The run summary reports received, eligible, discarded, duplicate, and inserted counts. Errors identify the failing phase and safe diagnostic details without emitting secrets or the full raw payload by default.
