## ADDED Requirements

### Requirement: Backlog is independent from a single weekly cycle
Una OT no finalizada al cierre SHALL incorporarse o actualizarse en una cola acumulativa de Backlog y conservar su semana de primer origen. Reprogramarla SHALL actualizar su seguimiento sin reemplazar su origen ni retirarla de la cola activa.

#### Scenario: Carry a pending order through multiple programming attempts
- **WHEN** una OT pendiente se programa, vuelve a quedar pendiente y se programa nuevamente en otra semana
- **THEN** conserva la semana de primer origen y acumula las reprogramaciones hasta finalizar

### Requirement: Closure is the finalization authority
El Backlog SHALL marcar una OT como finalizada solo despues de que el cierre semanal la reconcilie con un estado externo canonico FINALIZADO. La seleccion manual para programacion SHALL NOT finalizar ni borrar una OT de Backlog.

#### Scenario: Keep selected backlog order active before closure
- **WHEN** una OT de Backlog se selecciona para una semana pero aun no existe un cierre FINALIZADO
- **THEN** la OT permanece activa en seguimiento de Backlog
