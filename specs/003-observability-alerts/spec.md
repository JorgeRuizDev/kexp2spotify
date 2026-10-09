# Feature Specification: Observabilidad y alertas de ejecuciones

**Feature Branch**: `003-observability-alerts`

**Created**: 2026-10-10

**Status**: Draft

**Input**: User description: "Añade observabilidad a este proyecto. Quiero que la primera ejecución de un día me envíe un mensaje con un resumen del día anterior. Y quiero que si una ejecución falla después de 3 retries, me llegue un mensaje con la traza de error."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Recibir el resumen diario (Priority: P1)

Como operador del proceso programado, quiero recibir un resumen de las ejecuciones del día anterior en la primera ejecución de cada día para conocer rápidamente el estado de la operación sin revisar los logs manualmente.

**Why this priority**: Proporciona visibilidad proactiva del funcionamiento normal y permite detectar ausencia de ejecuciones o resultados inesperados.

**Independent Test**: Registrar ejecuciones de un día anterior, ejecutar el proceso por primera vez en un nuevo día y comprobar que el operador recibe un único resumen con los totales correctos.

**Acceptance Scenarios**:

1. **Given** existen ejecuciones del día anterior y no se ha enviado todavía su resumen, **When** comienza la primera ejecución del día actual, **Then** el operador recibe un mensaje con el número de ejecuciones correctas y fallidas, canciones recibidas y nuevas, y cambios realizados en el destino.
2. **Given** el resumen del día anterior ya fue enviado, **When** se ejecutan de nuevo una o más ejecuciones durante el mismo día, **Then** no se envía otro resumen diario.
3. **Given** no hubo ejecuciones el día anterior, **When** comienza la primera ejecución del día actual, **Then** el operador recibe un resumen que indica cero ejecuciones y cero resultados.

---

### User Story 2 - Recibir alertas de fallos definitivos (Priority: P1)

Como operador del proceso programado, quiero recibir una alerta cuando una ejecución no pueda completarse tras sus reintentos para poder diagnosticarla y actuar sin depender de la observación continua del programador.

**Why this priority**: Los fallos silenciosos pueden dejar desactualizada la colección o las playlists; una alerta accionable reduce el tiempo hasta la recuperación.

**Independent Test**: Forzar un fallo repetible, comprobar que se realizan tres reintentos después del intento inicial y verificar que se envía un único mensaje con el comando, el número de intentos y la traza del error.

**Acceptance Scenarios**:

1. **Given** una ejecución falla de forma transitoria, **When** el fallo ocurre antes de agotar los reintentos, **Then** el proceso vuelve a intentarlo y no envía una alerta de fallo definitivo.
2. **Given** una ejecución falla en el intento inicial y en sus tres reintentos, **When** termina el cuarto intento, **Then** el operador recibe un mensaje con el contexto de la ejecución y la traza del error, y el proceso termina con estado fallido.
3. **Given** una ejecución termina correctamente después de un reintento, **When** finaliza el proceso, **Then** no se envía una alerta de fallo y el historial refleja que la ejecución terminó correctamente.

---

### User Story 3 - Mantener diagnósticos seguros y resilientes (Priority: P2)

Como operador, quiero que la observabilidad no exponga credenciales ni convierta un problema del canal de avisos en un fallo adicional del proceso.

**Why this priority**: La información de diagnóstico debe ser útil sin aumentar el riesgo de seguridad ni impedir que el proceso complete su trabajo.

**Independent Test**: Simular un error del canal de mensajería y revisar que la ejecución conserva su resultado original, que el error queda registrado de forma segura y que no aparecen tokens o credenciales en mensajes ni logs.

**Acceptance Scenarios**:

1. **Given** el canal de notificación no está configurado o no está disponible, **When** se completa o falla una ejecución, **Then** el proceso conserva su código de salida y registra que el aviso no pudo enviarse sin revelar secretos.
2. **Given** la traza contiene información sensible o es demasiado extensa para el canal, **When** se construye la alerta, **Then** las credenciales se ocultan y la traza se limita a un tamaño seguro manteniendo el contexto principal.

### Edge Cases

- La primera ejecución del día se produce después de uno o más días sin ejecuciones; el resumen corresponde únicamente al día natural inmediatamente anterior.
- El proceso se ejecuta varias veces cerca del cambio de día; solo una ejecución debe reclamar el envío del resumen para cada día.
- El envío del resumen falla; una ejecución posterior debe poder volver a intentarlo sin duplicar un envío confirmado.
- Una ejecución falla después de haber completado parcialmente una operación; los reintentos no deben generar duplicados ni alterar el estado confirmado de ejecuciones previas.
- El reloj local y UTC cruzan una fecha distinta; la fecha del resumen debe seguir la zona horaria operativa configurada.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST conservar un historial consultable de cada ejecución, incluyendo fecha operativa, comando, estado, número de intentos, duración y contadores relevantes del procesamiento.
- **FR-002**: El sistema MUST identificar la primera ejecución de cada día usando la zona horaria operativa configurada.
- **FR-003**: En la primera ejecución de un día, el sistema MUST enviar un resumen de las ejecuciones del día natural anterior.
- **FR-004**: El resumen diario MUST incluir como mínimo ejecuciones totales, ejecuciones correctas, ejecuciones fallidas, canciones recibidas, canciones nuevas y cambios realizados en el destino.
- **FR-005**: El sistema MUST enviar como máximo un resumen diario confirmado para cada día resumido.
- **FR-006**: Si una ejecución falla, el sistema MUST realizar un intento inicial y hasta tres reintentos antes de declararla definitivamente fallida.
- **FR-007**: Si una ejecución continúa fallando tras los tres reintentos, el sistema MUST enviar una alerta con el comando, el número total de intentos y una traza diagnóstica del error.
- **FR-008**: Si una ejecución tiene éxito después de un reintento, el sistema MUST registrar el resultado correcto y MUST NOT enviar una alerta de fallo definitivo.
- **FR-009**: El sistema MUST permitir configurar de forma segura el destino de las notificaciones y el tiempo de espera para su entrega.
- **FR-010**: El sistema MUST ocultar credenciales, tokens y otros secretos de los mensajes, trazas y logs enviados por la funcionalidad.
- **FR-011**: Un fallo del canal de notificación MUST NOT cambiar el código de salida ni el resultado de la ejecución que originó el aviso.
- **FR-012**: El sistema MUST permitir reintentar el envío de un resumen que no haya sido confirmado como entregado, sin duplicar resúmenes ya confirmados.

### Key Entities

- **Registro de ejecución**: Resultado de una ejecución programada, con su fecha operativa, comando, estado, intentos, contadores y posible diagnóstico de error.
- **Resumen diario**: Agregación de los registros de ejecución correspondientes a un día operativo y mensaje asociado a ese día.
- **Estado de notificación**: Marca que indica si un resumen diario fue enviado y confirmado, para garantizar la idempotencia.
- **Alerta de fallo**: Mensaje dirigido al operador cuando una ejecución agotó sus reintentos, incluyendo contexto y diagnóstico seguro.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de las primeras ejecuciones de un día con un canal configurado generan un resumen del día anterior, sin más de un resumen confirmado por día resumido.
- **SC-002**: El 100% de los fallos persistentes generan una alerta después de exactamente cuatro intentos totales: uno inicial y tres reintentos.
- **SC-003**: Al menos el 99% de los mensajes de fallo contienen el comando, el número de intentos y una traza utilizable, sin credenciales detectables.
- **SC-004**: Un fallo del canal de notificación no cambia el código de salida ni impide completar el registro de la ejecución en el 100% de los casos comprobables.
- **SC-005**: Una ejecución que se recupera durante los reintentos no genera ninguna alerta de fallo definitivo.

## Assumptions

- El operador dispone de un canal de mensajería configurado y de las credenciales necesarias para enviar mensajes.
- Telegram es el canal de notificación inicial soportado por el producto; el diseño del requisito no impide añadir otros canales posteriormente.
- La zona horaria operativa existente del proyecto se utiliza para determinar los días naturales de los resúmenes.
- Los datos de historial y estado de notificación se conservan junto con los datos operativos existentes; las políticas de retención de largo plazo quedan fuera de esta funcionalidad.
- Los reintentos se aplican a las ejecuciones programadas de recopilación y actualización, no al flujo interactivo de autorización.
