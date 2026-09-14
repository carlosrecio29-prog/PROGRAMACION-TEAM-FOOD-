## Purpose

Mantiene una cola operativa acumulativa de OT pendientes hasta que su finalizacion sea confirmada por un cierre semanal verificable.

## ADDED Requirements

### Requirement: Persistent accumulated backlog
El sistema SHALL marcar automaticamente una OT como Pendiente en Backlog desde que un cierre la clasifique PENDIENTE o NO_ENCONTRADA. SHALL mantenerla activa hasta que un cierre posterior confirme que el ingeniero la FINALIZO. El Backlog SHALL ser consultable independientemente de la semana actualmente seleccionada.

#### Scenario: Preserve a pending order across weeks
- **WHEN** una OT queda PENDIENTE al cierre de una semana y no se finaliza en semanas posteriores
- **THEN** la OT sigue apareciendo en Backlog activo con su trazabilidad original

#### Scenario: Remove only after verified completion
- **WHEN** un cierre posterior clasifica una OT de Backlog como FINALIZADA
- **THEN** la OT deja de estar activa en Backlog y conserva su historial de seguimiento

### Requirement: Backlog lifecycle visibility
Cada OT de Backlog SHALL exponer al menos su estado de seguimiento, OT, especialidad, H-H, semana de primer origen, ultimo resultado de cierre, antiguedad y numero de reprogramaciones. Los estados activos SHALL distinguir PENDIENTE DISPONIBLE y PENDIENTE PROGRAMADA; el estado de finalizacion SHALL comunicar si fue finalizada o no por el ingeniero segun el ultimo cierre verificado.

#### Scenario: Review a reprogrammed pending order
- **WHEN** una OT activa de Backlog es seleccionada y guardada en una programacion semanal nueva
- **THEN** permanece visible en Backlog con estado PENDIENTE PROGRAMADA y se incrementa su trazabilidad de reprogramacion

### Requirement: Backlog outcome indicators
Backlog SHALL mostrar dos indicadores operativos: cantidad de OT movidas a Backlog y cantidad de OT finalizadas por el ingeniero. La lista principal SHALL mantener visibles las OT movidas que siguen pendientes y no finalizadas.

#### Scenario: Review backlog outcome indicators
- **WHEN** el usuario abre Backlog despues de procesar uno o mas cierres
- **THEN** ve el total de OT movidas, el total finalizado por el ingeniero y las OT pendientes activas que requieren seguimiento

### Requirement: Backlog candidate eligibility
Solo una OT de Backlog con estado PENDIENTE DISPONIBLE SHALL aparecer como candidata para una nueva programacion semanal. Una OT PENDIENTE PROGRAMADA SHALL NOT aparecer de nuevo como candidata mientras este asociada a una programacion abierta del mismo ciclo.

#### Scenario: Prevent duplicate same-cycle selection
- **WHEN** una OT pendiente ya esta programada en una semana abierta
- **THEN** la plataforma la muestra como PENDIENTE PROGRAMADA en Backlog y no permite seleccionarla como candidata duplicada

### Requirement: Backlog search and filtered entry
El usuario SHALL poder filtrar Backlog por estado, especialidad, area, antiguedad y texto. La plataforma SHALL aceptar un identificador de OT como contexto de entrada desde otro modulo y mostrar la OT correspondiente si sigue activa.

#### Scenario: Open backlog from a closure result
- **WHEN** el usuario abre Backlog desde una OT pendiente en el cierre semanal
- **THEN** Backlog se abre filtrado por esa OT y mantiene disponible el resto de filtros
