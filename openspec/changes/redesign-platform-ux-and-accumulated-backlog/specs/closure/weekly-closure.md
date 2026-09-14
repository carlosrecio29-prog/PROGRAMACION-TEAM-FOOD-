## ADDED Requirements

### Requirement: Hour-based weekly closure indicators
El cierre semanal SHALL mostrar H-H programadas, H-H finalizadas, H-H pendientes y porcentaje de cumplimiento calculados a partir de la programacion guardada y del resultado de cierre. Las H-H SHALL conservar la autoridad de los valores de programacion/backend.

#### Scenario: Review a completed closure
- **WHEN** el usuario consulta un cierre con OT finalizadas y pendientes
- **THEN** ve los cuatro indicadores con valores consistentes con las filas del resultado

#### Scenario: Review an unverified week
- **WHEN** la programacion aun no tiene cierre procesado
- **THEN** la interfaz identifica los indicadores pendientes de verificacion sin presentar H-H como cumplidas

### Requirement: Navigate pending results to backlog
Las filas de resultado PENDIENTE y NO_ENCONTRADA SHALL ofrecer una accion para abrir Backlog en el contexto de la OT. Las filas FINALIZADA SHALL NOT ofrecer una accion de envio a Backlog.

#### Scenario: Open a pending order in backlog
- **WHEN** el usuario selecciona la accion de Backlog de una fila PENDIENTE o NO_ENCONTRADA
- **THEN** la interfaz navega a Backlog filtrado por esa OT

#### Scenario: Keep finalized order out of backlog navigation
- **WHEN** el usuario revisa una fila FINALIZADA
- **THEN** la fila comunica su finalizacion y no presenta una accion para enviarla a Backlog

### Requirement: Mark non-finalized results as backlog pending
Al confirmar un cierre, cada OT con resultado PENDIENTE o NO_ENCONTRADA SHALL quedar marcada como Pendiente en Backlog. El resultado FINALIZADA SHALL comunicar que el ingeniero la finalizo y actualizar los indicadores de Backlog sin crear una pendiente activa.

#### Scenario: Confirm non-finalized closure results
- **WHEN** el usuario procesa un cierre con OT pendientes, no encontradas y finalizadas
- **THEN** las pendientes y no encontradas se marcan como Pendientes en Backlog y las finalizadas se registran como finalizadas por el ingeniero
