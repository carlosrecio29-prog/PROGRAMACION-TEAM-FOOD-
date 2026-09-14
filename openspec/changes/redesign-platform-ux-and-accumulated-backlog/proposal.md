## Why

La plataforma V2 conserva datos y reglas operativas valiosas, pero su interfaz concentra demasiadas decisiones, separa poco los flujos de planificacion, cierre y seguimiento, y hace que el backlog dependa artificialmente de una semana. Se necesita una experiencia integral que permita entender que hacer, programar, cerrar y recuperar pendientes sin perder filtros, informacion ni integraciones existentes.

## What Changes

- Redisenar el shell V2 completo: navegacion, encabezado de contexto, jerarquia de pantallas, estados, tablas, filtros, acciones y comportamiento responsive, preservando la identidad visual operativa de TEAM FOOD.
- Reorganizar los modulos actuales en flujos de Inicio, Planificacion, Cierre, Backlog y Administracion, sin eliminar la informacion o capacidades hoy disponibles en Resumen, Completar datos, PMP y Tecnicos.
- Ampliar Cierre semanal con indicadores de H-H programadas, H-H finalizadas/cumplidas, H-H pendientes y cumplimiento; el resultado debe enlazar las OT PENDIENTES o NO ENCONTRADAS al Backlog.
- Crear un Backlog acumulativo independiente de la semana que marque automaticamente como Pendiente las OT no finalizadas al cierre y las conserve hasta que un cierre confirme FINALIZADA, incluyendo trazabilidad de origen, antiguedad y reprogramaciones.
- Mostrar en Backlog los indicadores de OT movidas a Backlog y OT finalizadas por el ingeniero, junto con la lista persistente de OT pendientes no finalizadas.
- Cambiar el contrato V2 de backlog para que programar nuevamente una OT no la elimine como pendiente historica; debe distinguirse entre pendiente disponible para programar, pendiente programada y finalizada.
- Mantener al backend como unica autoridad de capacidad, H-H y estados externos normalizados; el frontend solo presenta dichos resultados.

## Capabilities

### New Capabilities

- `frontend/platform-ux`: Experiencia transversal, navegacion y patron visual operativo para toda la plataforma V2.
- `backlog/accumulated-backlog`: Cola acumulativa de OT pendientes con estado, trazabilidad y seguimiento hasta finalizacion.

### Modified Capabilities

- `closure/weekly-closure`: Indicadores de H-H y navegacion desde resultados pendientes hacia Backlog.
- `planning/weekly-planning`: Seleccion de candidatos desde Backlog sin retirar su seguimiento activo hasta el cierre finalizado.
- `frontend/weekly-programming-ux`: Programacion semanal integrada a la nueva jerarquia y al nuevo ciclo de backlog.
- `backlog/backlog-lifecycle`: Ciclo de vida del backlog deja de limitarse a la siguiente semana y conserva pendientes hasta finalizar.

## Impact

- Frontend V2: `frontend/src/App.jsx`, componentes por modulo, estilos compartidos, navegacion y pruebas de interfaz.
- Backend V2: servicios de programacion, cierre y una nueva consulta/contrato de backlog acumulativo; `api/index.py` y `frontend/src/api.js`.
- Persistencia V2: una migracion nueva e inmutable para estados, trazabilidad e historial de backlog; sin tocar migraciones aplicadas.
- QA: pruebas de ciclo completo pendiente -> reprogramada -> finalizada, contratos API, filtros, navegacion desde cierre y regresion de capacidad.
