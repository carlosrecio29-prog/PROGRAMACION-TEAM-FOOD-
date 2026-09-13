## Purpose

Ofrece una experiencia de programación semanal más estable, clara y controlable para revisar actividades, conservar el contexto de trabajo y operar cada grupo de actividades de forma independiente.

## ADDED Requirements

### Requirement: Stable selection context

La interfaz SHALL mantener la posición visual del usuario al seleccionar una actividad disponible o quitar una actividad de la programación actual. La acción SHALL actualizar los totales y las listas relacionadas sin desplazar la ventana ni el scroll interno de la tabla que el usuario está revisando.

#### Scenario: Select activity without page jump

- **WHEN** el usuario selecciona una OT en Equipo operando o Parada requerida
- **THEN** la OT pasa a la selección actual, se actualizan sus totales y el usuario permanece en la misma posición de la página y de la tabla

#### Scenario: Remove activity without page jump

- **WHEN** el usuario quita una OT desde la selección actual
- **THEN** la OT deja de estar seleccionada, se actualizan los totales y el usuario permanece en la misma posición de la página

### Requirement: Independent activity-group filters

La interfaz SHALL mostrar controles de filtro independientes para Equipo operando, Parada requerida y Backlog. Cada grupo SHALL tener su propio estado de área y búsqueda, y modificar un grupo no SHALL cambiar los resultados visibles ni los valores de filtro de los otros grupos.

#### Scenario: Filter operating activities independently

- **WHEN** el usuario establece una búsqueda o área en Equipo operando
- **THEN** solo se filtran las actividades de Equipo operando y Parada requerida y Backlog conservan sus resultados y filtros

#### Scenario: Filter required-stop activities independently

- **WHEN** el usuario establece una búsqueda o área en Parada requerida
- **THEN** solo se filtran las actividades de Parada requerida y los otros grupos no se modifican

#### Scenario: Preserve filters while selecting

- **WHEN** el usuario selecciona o quita una OT después de haber aplicado filtros en uno o más grupos
- **THEN** cada grupo conserva sus filtros y la actividad seleccionada se refleja sin resetear búsquedas ni áreas

### Requirement: Clear weekly workflow hierarchy

La interfaz SHALL presentar la pantalla en un orden que permita identificar rápidamente el contexto de semana/especialidad, el estado de capacidad, las actividades disponibles, la selección actual y las acciones de guardado. La reorganización SHALL conservar las etiquetas operativas y distinguir visualmente Equipo operando, Parada requerida y Backlog.

#### Scenario: Review weekly programming in edit mode

- **WHEN** el usuario abre una semana en modo edición
- **THEN** puede identificar el contexto activo, revisar capacidad, filtrar cada grupo, consultar la selección actual y encontrar Guardar cambios sin depender de recorrer bloques ambiguos

#### Scenario: Consult saved programming in read-only mode

- **WHEN** el usuario consulta una programación guardada sin editar
- **THEN** la interfaz conserva la jerarquía de revisión, muestra la selección actual como solo lectura y no habilita acciones de modificación

### Requirement: Preserve domain and API behavior

La interfaz SHALL continuar mostrando HH, capacidad, metas, reservas, estados y resultados calculados por el backend sin recalcular reglas de dominio. La reorganización SHALL usar los contratos V2 existentes y no SHALL alterar la persistencia de programación, backlog, cierres o reportes.

#### Scenario: Capacity remains backend-authoritative

- **WHEN** se seleccionan o quitan actividades
- **THEN** la interfaz refleja los valores derivados con la lógica existente y mantiene las validaciones de capacidad sin introducir una fórmula frontend alternativa

#### Scenario: Save and export remain compatible

- **WHEN** el usuario guarda una programación válida o exporta una programación guardada
- **THEN** se utilizan los flujos V2 existentes y los filtros visuales no cambian el conjunto persistido ni el contrato de exportación
