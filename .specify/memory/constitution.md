<!--
Sync Impact Report
- Version change: unversioned scaffold -> 1.0.0
- Modified principles: placeholder principles -> SOLID, Python typing, source/destination
  agnosticism, and Spec Kit context gate
- Added sections: Architecture & Integration Constraints; Development Workflow & Quality Gates
- Removed sections: none
- Follow-up TODOs: create .specify/memory/context.md; confirm the original ratification date
-->

# KEXP2Spotify Constitution

## Core Principles

### I. Diseño SOLID y responsabilidades claras

El código MUST seguir los principios SOLID. Cada módulo, clase y función MUST tener una
responsabilidad clara y una interfaz explícita; las dependencias MUST apuntar a abstracciones,
las implementaciones MUST poder sustituirse sin cambiar los consumidores y las interfaces MUST
ser pequeñas y enfocadas. Cualquier excepción MUST documentar por qué reduce complejidad o
riesgo. Esto mantiene el sistema extensible, comprobable y comprensible.

### II. Tipado estático de Python

Todo código Python de producción MUST estar anotado con tipos, incluidos parámetros, valores de
retorno, atributos y estructuras públicas. El proyecto MUST ejecutar un comprobador de tipos en
los controles de calidad definidos por el proyecto; los usos de `Any`, casts inseguros y tipos
ignorados MUST ser excepcionales, localizados y justificados. El tipado es un contrato de diseño,
no solo documentación.

### III. Origen y destino agnósticos mediante contratos estándar

El origen de las canciones y el destino MUST ser intercambiables y no pueden filtrarse al núcleo
de dominio. Las integraciones MUST exponerse mediante contratos REST o SDKs equivalentes,
documentados y comprobables; no se admiten mecanismos propietarios, acoplamientos implícitos,
automatización de interfaz ni protocolos ad hoc. Los adaptadores MUST aislar autenticación,
serialización, paginación, límites y errores de cada proveedor, y el núcleo MUST depender solo de
abstracciones propias del dominio.

### IV. Contexto obligatorio en cada paso de Spec Kit

Antes de ejecutar cualquier paso de Spec Kit —incluidos specify, clarify, plan, tasks,
implement, analyze, checklist y constitution— el agente MUST leer íntegramente
`.specify/memory/context.md`. Si el fichero no existe, no puede leerse o está desactualizado para
el paso, el agente MUST detener el paso y registrar la incidencia antes de modificar otros
artefactos. Este fichero es una entrada obligatoria de gobernanza y no puede sustituirse por
suposiciones del agente.

## Architecture & Integration Constraints

El sistema MUST separar dominio, casos de uso, puertos y adaptadores. Las dependencias externas
MUST entrar a través de puertos tipados y los adaptadores REST/SDK MUST poder probarse con dobles
de contrato. Los modelos internos no pueden depender de formatos de proveedores. Las operaciones
de integración MUST definir explícitamente timeouts, errores, reintentos seguros, límites de
petición y observabilidad suficiente para diagnosticar fallos sin exponer secretos.

## Development Workflow & Quality Gates

Cada cambio MUST incluir pruebas proporcionales al riesgo: pruebas unitarias para reglas de
dominio, pruebas de contrato para puertos y adaptadores, y pruebas de integración cuando cambie
la interacción con un proveedor. Antes de aceptar un cambio, la revisión MUST comprobar el
cumplimiento de esta constitución, el tipado, la separación de responsabilidades y la ausencia
de acoplamiento accidental a un origen o destino concreto. Los incumplimientos MUST corregirse o
quedar justificados explícitamente en la revisión.

## Governance

Esta constitución prevalece sobre prácticas locales en conflicto. Toda modificación MUST
actualizar el informe de impacto, explicar el cambio de versión y conservar los principios que
continúen siendo aplicables. La versión sigue SemVer: MAJOR para eliminar o redefinir reglas de
forma incompatible, MINOR para añadir o ampliar principios o secciones, y PATCH para aclaraciones
sin cambio semántico. Cada revisión de código y cada paso de Spec Kit MUST verificar el
cumplimiento. Las excepciones requieren una justificación escrita, alcance limitado, responsable
y fecha de revisión; no pueden convertirse en una práctica general por omisión.


**Version**: 1.0.0 | **Ratified**: TODO(RATIFICATION_DATE): confirmar fecha original de adopción | **Last Amended**: 2026-10-09
