# Research: KEXP Play Crawler

## Decision: Python estándar con adaptadores tipados y `httpx` para HTTP

**Rationale**: El proyecto ya requiere Python >=3.11 y el crawler es un proceso batch pequeño. `httpx` ofrece cliente reutilizable, timeouts explícitos y una jerarquía diferenciada para errores de red y respuestas HTTP. La implementación configurará timeout de conexión, lectura, escritura y pool, en lugar de permitir una espera indefinida.

**Alternatives considered**: `urllib.request` reduce dependencias pero hace más incómodas las pruebas y el control fino de timeouts; `requests` es válido pero no aporta una ventaja necesaria para este diseño.

**Sources**: [HTTPX timeouts](https://www.python-httpx.org/advanced/timeouts/), [HTTPX exceptions](https://www.python-httpx.org/exceptions/).

## Decision: `pydantic-settings` con `YamlConfigSettingsSource` y entorno por encima de YAML

**Rationale**: El usuario exige YAML cargado siempre y variables de entorno sobrescribibles. `pydantic-settings` proporciona una fuente YAML y permite personalizar el orden de fuentes; el diseño usará un `YamlConfigSettingsSource` obligatorio seguido por `EnvSettingsSource`, dejando las variables de entorno con mayor prioridad. `PyYAML` se incluirá mediante el extra YAML. Los modelos validarán URL, enteros positivos, timeouts y rutas antes de abrir la fuente o la base de datos.

**Alternatives considered**: Leer YAML con PyYAML y aplicar manualmente `os.environ` duplicaría reglas de precedencia y validación; un `.env` no satisface el requisito de YAML obligatorio.

**Sources**: [Pydantic Settings: fuentes y precedencia](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/), [`YamlConfigSettingsSource`](https://github.com/pydantic/pydantic-settings/blob/main/pydantic_settings/sources/providers/yaml.py), [extra YAML de pydantic-settings](https://github.com/pydantic/pydantic-settings/blob/main/pyproject.toml).

## Decision: SQLite con `sqlite3` y transacción por ejecución

**Rationale**: SQLite está pedido explícitamente y la biblioteca estándar evita un ORM innecesario. Se usará una tabla de canciones con índice único en `track_id`, consultas ordenadas por timestamp de incorporación para obtener las N últimas y una transacción para insertar el lote. La consulta externa y la validación ocurren antes de iniciar la transacción, de modo que los fallos no dejan inserciones parciales.

**Alternatives considered**: SQLAlchemy añade abstracción útil para aplicaciones mayores, pero no es necesaria para un proceso local de una tabla; una base de datos en memoria no sirve para ejecuciones sucesivas.

## Decision: Paginar solo si la respuesta del proveedor lo exige

**Rationale**: El límite M es configurable y el cliente debe respetarlo. El adaptador interpretará la forma de colección documentada por KEXP, conservará solo los elementos necesarios y seguirá enlaces/parámetros de paginación únicamente hasta reunir M elementos o agotar resultados. Una respuesta malformada falla de forma explícita.

**Alternatives considered**: Descargar un número fijo grande desperdicia red y rompe el contrato configurable; asumir una única forma de JSON haría frágil el adaptador.

## Decision: CLI con códigos de salida y logs estructurados sencillos

**Rationale**: El cronjob necesita distinguir éxito sin novedades, éxito con inserciones y fallo. La entrada CLI cargará configuración, ejecutará el caso de uso y emitirá un resumen con recibidas/filtradas/duplicadas/insertadas. Los errores no incluirán secretos ni el JSON completo en logs por defecto.

**Alternatives considered**: No devolver código de salida dificulta alertas de cron; una API web queda fuera de alcance.
