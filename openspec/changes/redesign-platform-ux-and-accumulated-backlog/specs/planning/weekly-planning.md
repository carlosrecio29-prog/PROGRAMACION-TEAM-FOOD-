## ADDED Requirements

### Requirement: Preserve active backlog while reprogramming
Guardar una OT activa de Backlog en una nueva programacion semanal SHALL registrar la programacion como una reprogramacion de esa OT sin eliminar su seguimiento activo. La OT solo dejara de ser Backlog activo cuando un cierre confirme FINALIZADA.

#### Scenario: Reprogram a pending backlog order
- **WHEN** el usuario guarda una OT PENDIENTE DISPONIBLE de Backlog en una programacion semanal
- **THEN** la OT queda en la programacion guardada y en Backlog se muestra como PENDIENTE PROGRAMADA

### Requirement: Preserve scheduling exclusivity
El sistema SHALL impedir que una OT se seleccione mas de una vez en programaciones abiertas que se solapen. La conservacion de una OT en Backlog como seguimiento SHALL NOT equivaler a una segunda asignacion de programacion.

#### Scenario: Attempt duplicate weekly assignment
- **WHEN** el usuario intenta agregar una OT que ya esta programada en una semana abierta incompatible
- **THEN** el sistema rechaza la seleccion e informa el conflicto de programacion
