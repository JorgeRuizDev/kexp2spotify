# Implementation Plan: KEXP Play Crawler

**Branch**: `001-kexp-play-crawler` | **Date**: 2026-10-09 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-kexp-play-crawler/spec.md`

## Summary

Construir un crawler ejecutable por cronjob que consulte las reproducciones recientes de KEXP, filtre exclusivamente `trackplay`, deduplicate por `track_id` contra las N canciones más recientes y persista las nuevas junto con sus metadatos y JSON original en SQLite. La configuración se cargará siempre desde YAML y se combinará con variables de entorno de mayor precedencia mediante `pydantic-settings`. El diseño separa configuración, adaptador HTTP, dominio de canciones, caso de uso de deduplicación y repositorio SQLite.

## Technical Context

**Language/Version**: Python >=3.11 (ya fijado en `pyproject.toml`)

**Primary Dependencies**: `pydantic`/`pydantic-settings` con soporte YAML, `PyYAML`, `httpx`, `pytest`, `pytest-httpx`, `mypy` y `ruff`

**Storage**: SQLite mediante la biblioteca estándar `sqlite3`; JSON completo serializado en una columna de texto

**Testing**: `pytest` para unitarias e integración; dobles HTTP para el contrato KEXP; `mypy` y `ruff` como controles estáticos

**Target Platform**: Proceso Python no interactivo en servidor Linux invocado por cronjob

**Project Type**: CLI/proceso batch interno

**Performance Goals**: Procesar hasta M reproducciones y finalizar en menos de 60 segundos en condiciones normales; una única consulta por ejecución salvo que la respuesta requiera paginación

**Constraints**: YAML obligatorio; variables de entorno sobrescriben YAML; no modificar SQLite si la consulta o validación de respuesta falla; URLs, M, N, timeout y ruta de SQLite configurables

**Scale/Scope**: Una radio, ejecuciones periódicas, SQLite local, volumen histórico creciente y respuestas acotadas por M; sin API web ni integración con Spotify en esta feature

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

*GATE: PASS*

- **SOLID y responsabilidades claras**: configuración, fuente KEXP, dominio, caso de uso y persistencia se diseñan como componentes sustituibles.
- **Tipado estático**: todas las interfaces públicas y modelos tendrán anotaciones; el plan incluye `mypy`.
- **Origen/destino agnósticos**: KEXP y SQLite estarán detrás de puertos/adaptadores; el dominio no dependerá de su JSON ni de `sqlite3`.
- **Integraciones comprobables**: el adaptador HTTP tendrá timeout, errores tipados, límite M y pruebas de contrato con doble HTTP.
- **Pruebas proporcionales**: unitarias para deduplicación/configuración, contrato para KEXP e integración para SQLite y flujo completo.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file ($speckit-plan command output)
├── research.md          # Phase 0 output ($speckit-plan command)
├── data-model.md        # Phase 1 output ($speckit-plan command)
├── quickstart.md        # Phase 1 output ($speckit-plan command)
├── contracts/           # Phase 1 output ($speckit-plan command)
└── tasks.md             # Phase 2 output ($speckit-tasks command - NOT created by $speckit-plan)
```

### Source Code (repository root)
-->

```text
src/
└── kexp2spotify/
    ├── config.py          # YAML + entorno, validación tipada
    ├── domain.py          # modelos y reglas sin dependencias externas
    ├── ports.py           # contratos de fuente y repositorio
    ├── kexp_client.py     # adaptador HTTP de KEXP
    ├── sqlite_repository.py
    ├── crawler.py         # caso de uso/orquestación
    └── cli.py             # entrada de cronjob y códigos de salida

tests/
├── unit/
├── contract/
└── integration/

config.example.yml
```

**Structure Decision**: Proyecto Python único con paquete bajo `src/`, puertos explícitos para fuente y almacenamiento, adaptadores concretos separados y tests organizados por tipo de contrato. `main.py` podrá delegar en `kexp2spotify.cli` durante la implementación para conservar una entrada sencilla.

## Constitution Check — Post-Design

*GATE: PASS*

- El modelo de dominio y los puertos no dependen de KEXP, SQLite, HTTPX ni del formato JSON externo.
- La configuración queda aislada en un modelo tipado y se valida antes de crear efectos externos.
- El adaptador de KEXP encapsula URL, límites, paginación, timeouts, respuestas HTTP y errores.
- El repositorio SQLite encapsula esquema, índice único, ventana N y transacción de lote.
- Las pruebas previstas cubren dominio, configuración, contrato HTTP, persistencia y ejecución completa.
- No se detectan violaciones de SOLID, tipado estático, agnosticismo de origen/destino ni gates de calidad.

## Complexity Tracking

No hay violaciones de la constitución que requieran justificación.
