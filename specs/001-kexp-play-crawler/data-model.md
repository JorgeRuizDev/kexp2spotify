# Data Model: KEXP Play Crawler

## SongRecord

Representa una reproducción válida de tipo `trackplay` preparada para el pipeline.

| Field | Type | Required | Rules |
|---|---|---:|---|
| `id` | integer | yes | Identificador de la reproducción KEXP; se conserva como dato auxiliar |
| `track_id` | string | yes | Identidad canónica y clave única de deduplicación |
| `song` | string | yes | Nombre de la canción; no vacío |
| `artist` | string | yes | Artista; no vacío |
| `album` | string/null | no | Se conserva vacío/nulo si falta |
| `release_date` | date/string null | no | Se conserva el valor original normalizado si es válido |
| `captured_at` | datetime | yes | Timestamp UTC de incorporación local |
| `raw_json` | JSON text | yes | Objeto completo recibido, sin perder campos desconocidos |
| `airdate` | datetime/string null | no | Fecha de emisión del proveedor, extraída si existe |
| `play_type` | string | yes | Debe ser exactamente `trackplay` |

## Constraints

- `track_id` tiene un índice único para garantizar idempotencia dentro de la base de datos.
- La ventana de deduplicación se obtiene ordenando por `captured_at` descendente y tomando N registros.
- El histórico no se purga como parte de esta feature.
- Los campos de proveedor no modelados permanecen en `raw_json`.

## Configuration

| Field | Type | Required | Rules |
|---|---|---:|---|
| `kexp_plays_url` | URL | yes | URL de la colección de reproducciones |
| `fetch_limit` | positive integer | yes | M, número máximo de reproducciones a considerar |
| `deduplication_window` | positive integer | yes | N, número de canciones recientes comparadas |
| `database_path` | path | yes | Ruta de SQLite |
| `request_timeout_seconds` | positive number | yes | Timeout total o base del cliente HTTP |
| `config_file` | path | yes | YAML que debe existir y cargarse siempre |

Environment variables use the configured prefix and override YAML values after source merging. Exact names and nesting belong to the implementation contract and must be documented in the example configuration.

## State Flow

`received` → `validated_trackplay` → `deduplication_candidate` → `persisted`.

Invalid or non-`trackplay` items end in `discarded`; network, schema, configuration, or persistence failures end the execution without committing the current batch.
