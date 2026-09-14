## MODIFIED Requirements

### Requirement: Clear weekly workflow hierarchy
La interfaz SHALL presentar la programacion semanal dentro del flujo de Planificacion, identificando semana, especialidad, capacidad, actividades disponibles, seleccion actual y acciones de guardado. La reorganizacion SHALL conservar las etiquetas operativas, distinguir Equipo operando, Parada requerida y candidatos de Backlog, e indicar cuando una OT de Backlog sigue pendiente de finalizacion aunque haya sido reprogramada.

#### Scenario: Review weekly programming in edit mode
- **WHEN** el usuario abre una semana en modo edicion
- **THEN** puede identificar el contexto activo, revisar capacidad, filtrar cada grupo, consultar la seleccion actual, distinguir el origen Backlog y encontrar Guardar cambios sin depender de recorrer bloques ambiguos

#### Scenario: Consult saved programming in read-only mode
- **WHEN** el usuario consulta una programacion guardada sin editar
- **THEN** la interfaz conserva la jerarquia de revision, muestra la seleccion actual como solo lectura y no habilita acciones de modificacion

## ADDED Requirements

### Requirement: Distinguish backlog candidates from backlog tracking
La programacion semanal SHALL listar como candidatas solo las OT PENDIENTE DISPONIBLE de Backlog. Cuando una OT de Backlog se programe, su origen SHALL seguir siendo visible en la seleccion semanal sin presentarla nuevamente como candidata mientras este programada.

#### Scenario: Select an available backlog candidate
- **WHEN** el usuario selecciona una OT PENDIENTE DISPONIBLE de Backlog y guarda la semana
- **THEN** la OT aparece en la seleccion con origen Backlog y deja de aparecer como candidata duplicada
