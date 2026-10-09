# Feature Specification: KEXP Play Crawler

**Feature Branch**: `001-kexp-play-crawler`

**Created**: 2026-10-09

**Status**: Draft

**Input**: User description: "Implementar un crawler sencillo que consulte las últimas canciones de KEXP, descarte las ya conocidas dentro de las N últimas canciones, guarde las nuevas en SQLite y las deje disponibles para el siguiente paso del pipeline, con ejecución inicial mediante cronjob."

## Clarifications

### Session 2026-10-09

- Q: ¿Qué identificador debe determinar que una canción ya está almacenada: `track_id`, el identificador de la reproducción (`id`) o una combinación de campos? → A: `track_id`.
- Q: ¿La base de datos debe conservar todo el histórico de canciones capturadas o eliminar las canciones que queden fuera de las N últimas? → A: Conservar todo el histórico; N solo limita la deduplicación.
- Aporte adicional: Los límites, las URLs de KEXP y el resto de parámetros operativos deben configurarse mediante un archivo YAML cargado siempre; las variables de entorno pueden sobrescribir sus valores, usando configuración tipada basada en `pydantic-settings`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Recopilar nuevas canciones emitidas (Priority: P1)

Como operador del pipeline, quiero ejecutar una recopilación periódica de las últimas canciones emitidas por KEXP para que las canciones nuevas queden disponibles para los pasos posteriores.

**Why this priority**: Es el objetivo principal de la feature y proporciona la entrada de datos necesaria para todo el pipeline.

**Independent Test**: Con una respuesta conocida del servicio de KEXP y una base de datos vacía, ejecutar una recopilación y comprobar que se guardan únicamente los elementos válidos de tipo canción.

**Acceptance Scenarios**:

1. **Given** una respuesta válida con canciones y otros tipos de reproducción, **When** se ejecuta la recopilación, **Then** solo se consideran y almacenan los elementos cuyo `play_type` sea `trackplay`.
2. **Given** una respuesta válida con canciones nuevas, **When** termina la recopilación, **Then** cada canción nueva queda persistida con sus datos principales y el JSON completo para el siguiente paso del pipeline.
3. **Given** una ejecución programada sin canciones nuevas, **When** termina la recopilación, **Then** la ejecución finaliza correctamente sin crear duplicados.

### User Story 2 - Evitar duplicados entre ejecuciones (Priority: P1)

Como operador del pipeline, quiero que cada ejecución compare las canciones obtenidas con las últimas canciones ya almacenadas para no procesar repetidamente la misma canción.

**Why this priority**: La ejecución será periódica; sin deduplicación, el almacenamiento y los pasos posteriores recibirían datos repetidos.

**Independent Test**: Prellenar la base de datos con una ventana de canciones conocidas, devolver una mezcla de canciones conocidas y nuevas, y comprobar que solo se insertan las nuevas dentro de la ventana configurada.

**Acceptance Scenarios**:

1. **Given** una canción cuyo identificador ya está entre las N últimas canciones almacenadas, **When** se procesa la respuesta, **Then** no se inserta otra copia.
2. **Given** una canción cuyo identificador no está entre las N últimas canciones almacenadas, **When** se procesa la respuesta, **Then** se inserta como nueva canción.
3. **Given** una respuesta que contiene el mismo identificador más de una vez, **When** se procesa, **Then** se guarda una sola vez.

### User Story 3 - Reanudar de forma segura tras fallos (Priority: P2)

Como operador del cronjob, quiero que los fallos de red o de datos no corrompan la información ya almacenada ni conviertan una ejecución parcial en duplicados.

**Why this priority**: Las ejecuciones desatendidas deben ser diagnosticables y repetibles sin intervención manual frecuente.

**Independent Test**: Simular un error del servicio y una respuesta con registros inválidos, y comprobar que los datos previamente persistidos permanecen intactos y que la ejecución informa del fallo.

**Acceptance Scenarios**:

1. **Given** que el servicio externo no responde correctamente, **When** se ejecuta la recopilación, **Then** no se modifican los registros existentes y el resultado indica el error.
2. **Given** elementos sin los campos necesarios para representar una canción, **When** se procesa la respuesta, **Then** se omiten esos elementos y se conserva el resto de canciones válidas.
3. **Given** que el proceso se ejecuta de nuevo tras un fallo, **When** recibe los mismos datos, **Then** no genera duplicados de los registros que ya se hubieran confirmado.

### Edge Cases

- La respuesta está vacía o no contiene elementos de tipo `trackplay`.
- La respuesta tiene una estructura inesperada o no puede interpretarse como una colección de reproducciones.
- Una canción carece de uno o más datos opcionales, como álbum o fecha de lanzamiento; debe conservarse con esos campos vacíos, sin inventar valores.
- Una canción carece de identificador o de los datos mínimos para identificarla; debe omitirse y registrarse como elemento no procesable.
- La misma canción aparece varias veces en la respuesta actual.
- La base de datos ya contiene menos de N canciones.
- Se ejecutan dos recopilaciones muy próximas entre sí.
- El servicio devuelve más elementos que el límite M solicitado o configurado.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST consultar la fuente de reproducciones de KEXP y solicitar las últimas M reproducciones, donde M sea configurable.
- **FR-002**: El sistema MUST considerar exclusivamente reproducciones cuyo `play_type` sea exactamente `trackplay`.
- **FR-003**: El sistema MUST identificar y deduplicar una canción mediante `track_id` y MUST rechazar elementos sin un `track_id` válido.
- **FR-004**: El sistema MUST comparar las canciones recibidas con los identificadores de las N últimas canciones almacenadas, donde N sea configurable.
- **FR-005**: El sistema MUST insertar solo canciones que no estén presentes en esa ventana de N canciones y MUST evitar duplicados dentro de una misma ejecución.
- **FR-006**: El sistema MUST persistir, como mínimo, el nombre de la canción, artista, álbum, fecha de lanzamiento, identificador, timestamp de incorporación y JSON completo de la reproducción.
- **FR-007**: El sistema MUST conservar los campos opcionales ausentes como valores vacíos o nulos, sin sustituirlos por información inventada.
- **FR-008**: El sistema MUST almacenar los registros en una base de datos SQLite local y reutilizable entre ejecuciones.
- **FR-009**: El sistema MUST hacer que las canciones nuevas insertadas queden consultables por el siguiente paso del pipeline, incluyendo su JSON completo.
- **FR-010**: El sistema MUST tratar una respuesta sin canciones nuevas como una ejecución válida y sin cambios en la base de datos.
- **FR-011**: El sistema MUST informar de los errores de consulta, respuesta inválida o persistencia con suficiente detalle para diagnosticar el cronjob.
- **FR-012**: El sistema MUST preservar los registros confirmados antes de un fallo y permitir repetir la ejecución sin duplicarlos.
- **FR-013**: El sistema MUST soportar ejecución no interactiva y configuración adecuada para ser invocado por un cronjob.
- **FR-014**: El sistema MUST mantener separadas la obtención de reproducciones, la deduplicación y la persistencia para que cada responsabilidad pueda probarse de forma independiente.
- **FR-015**: El sistema MUST cargar un archivo YAML de configuración en cada ejecución; la ausencia, inaccesibilidad o invalidez del archivo MUST impedir la ejecución y producir un diagnóstico claro.
- **FR-016**: El sistema MUST permitir configurar mediante YAML, como mínimo, la URL de la fuente de KEXP, el límite M de reproducciones, el límite N de deduplicación y la ruta de la base de datos.
- **FR-017**: El sistema MUST permitir sobrescribir mediante variables de entorno los valores definidos en el YAML, aplicando de forma determinista la precedencia de las variables de entorno sobre el archivo.
- **FR-018**: La configuración MUST validarse mediante un modelo tipado basado en `pydantic-settings`, y los valores ausentes, inválidos o incompatibles MUST producir un error antes de consultar la fuente o modificar la base de datos.

### Key Entities

- **Reproducción**: Elemento recibido de la fuente externa; contiene el tipo de reproducción, identificadores, metadatos musicales y el JSON original.
- **Canción almacenada**: Representación persistida de una reproducción válida de tipo `trackplay`, con sus datos normalizados, timestamp de incorporación y JSON completo.
- **Ventana de deduplicación**: Las N canciones más recientemente almacenadas contra las que se comparan las nuevas reproducciones.
- **Ejecución de recopilación**: Una invocación del crawler, con parámetros M y N, resultado, errores y cantidad de elementos recibidos, descartados e insertados.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: En una ejecución normal, al menos el 100% de las reproducciones válidas con `play_type=trackplay` que no estén en la ventana configurada quedan disponibles para el siguiente paso del pipeline.
- **SC-002**: En una ejecución repetida con la misma respuesta, el número de nuevos registros insertados después de la primera ejecución es 0.
- **SC-003**: Una ejecución programada procesa una respuesta de hasta M elementos y deja el resultado persistido en menos de 60 segundos en condiciones normales de red y almacenamiento local.
- **SC-004**: Ante un error del servicio externo, el 100% de los registros confirmados antes del error permanece recuperable y la ejecución deja un diagnóstico accionable.
- **SC-005**: El operador puede verificar para cada canción almacenada el nombre, artista, álbum, fecha de lanzamiento, identificador, timestamp de incorporación y JSON original sin consultar de nuevo la fuente externa.

## Assumptions

- La fuente externa proporciona una colección ordenable de reproducciones recientes y permite solicitar o limitar el número M de resultados.
- El identificador principal para deduplicar es el identificador de canción (`track_id`); el identificador de la reproducción se conserva dentro del JSON original y puede almacenarse como dato auxiliar.
- M y N tendrán valores configurables con valores predeterminados razonables para una ejecución periódica; el alcance de esta feature no incluye una interfaz de administración.
- El YAML de configuración se carga siempre y las variables de entorno actúan como sobrescrituras para facilitar el despliegue mediante cronjob.
- La configuración se implementará mediante `pydantic-settings` o el mecanismo equivalente del proyecto para combinar y validar YAML y variables de entorno.
- La ruta del archivo YAML podrá definirse mediante una variable de entorno o el valor predeterminado documentado por el proyecto.
- SQLite se ubicará en una ruta configurable y será accesible por el usuario que ejecute el cronjob.
- La base de datos conserva todo el histórico de canciones capturadas; N limita únicamente la ventana usada para deduplicar y no implica purgar registros antiguos.
- La autenticación no es necesaria para consultar la fuente indicada.
- El siguiente paso del pipeline leerá las canciones desde la base de datos; no se incluye en esta feature la integración con Spotify ni otro destino.
