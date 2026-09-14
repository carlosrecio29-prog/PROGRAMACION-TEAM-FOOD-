## Context

La UI V2 actual concentra la navegacion en `App.jsx`, usa componentes de programacion y cierre separados, y dispone de un `backlog_v2` con una sola fila por OT. El flujo vigente elimina esa fila al volver a programar la OT, por lo que no puede representar una cola acumulativa hasta finalizacion. Vease `proposal.md` para la motivacion y los deltas de especificacion para el contrato observable.

## Goals / Non-Goals

**Goals:**

- Crear un shell frontend por flujos operativos y componentes reutilizables sin recalcular reglas de dominio en cliente.
- Dar a Backlog una fuente V2 propia, consultable por filtros y navegable desde Cierre.
- Conservar el historial y la primera procedencia de una OT, aun cuando se reprograme varias veces.
- Mantener compatibilidad con los contratos V2 existentes mientras se agregan endpoints de Backlog.

**Non-Goals:**

- Reescribir V1, cambiar la formula de capacidad, cambiar el sistema externo o introducir autenticacion/RLS como parte de esta entrega.
- Convertir el historial de programacion cerrada en editable.
- Eliminar datos de backlog o migraciones V2 existentes.

## Decisions

### Modelar Backlog como seguimiento y no como lista de candidatos

Se agregara una migracion V2 nueva que extienda el registro actual con estado activo, primer origen, ultima programacion, contador de reprogramaciones, ultimo cierre y timestamps auditables. Un registro activo tendra estados `PENDIENTE_DISPONIBLE` o `PENDIENTE_PROGRAMADA`; la finalizacion por el ingeniero se conservara como resultado confirmado de cierre/historial y dejara de aparecer en las consultas activas. Se preservara unicidad por OT para el estado de seguimiento actual y se derivara el historial desde programaciones/cierres, evitando duplicar OT activas.

Alternativa descartada: borrar e insertar un nuevo backlog en cada semana. Pierde antiguedad y no satisface la cola acumulativa solicitada.

### Separar elegibilidad de seguimiento

La consulta de candidatos de Programacion devolvera solo `PENDIENTE_DISPONIBLE`; la consulta de Backlog mostrara tambien `PENDIENTE_PROGRAMADA`. Programar una OT cambia su estado de seguimiento y registra la reprogramacion, pero no crea una segunda asignacion. Cerrar como FINALIZADA la desactiva; cerrar como PENDIENTE o NO_ENCONTRADA la devuelve a disponible si no existe otra programacion abierta incompatible.

Alternativa descartada: mostrar todas las OT activas como candidatas. Violaria la exclusividad de una OT en una programacion abierta y permitiria duplicados.

### Exponer Backlog mediante contrato V2 explicito

Se agregara un endpoint de lectura de Backlog con filtros de OT, estado, especialidad, area, antiguedad y busqueda, mas indicadores de OT movidas y OT finalizadas por el ingeniero. Las respuestas de Cierre incluiran o expondran una clave estable de OT que el frontend usara para navegar. El endpoint de programacion conservara su forma compatible, pero su semantica de mover/eliminar backlog se sustituira por transiciones de seguimiento.

Alternativa descartada: reconstruir Backlog exclusivamente en React con datos de cada semana. No permite acumulacion, filtros globales ni trazabilidad confiable.

### Construir el frontend por shell y features

`App.jsx` se reducira a orquestacion de contexto y rutas de vista. Se extraeran shell, navegacion, patrones compartidos y features de inicio, planificacion, cierre, backlog y administracion. La navegacion de Cierre a Backlog mantendra el identificador de OT en estado de aplicacion, sin depender de scroll ni de una URL externa obligatoria. Las tablas conservaran controles locales y accesibles; se priorizara foco visible, etiquetas y disposicion responsive.

Alternativa descartada: una sustitucion visual monolitica en `App.jsx`. Aumentaria el riesgo de regresion y mantendria la concentracion actual de responsabilidades.

### Mantener H-H y estados como valores backend-autoritativos

Los indicadores de Cierre se construiran con H-H programadas y resultados de cierre entregados por V2. El frontend podra sumar filas presentadas para una visualizacion consistente, pero no definira formulas ni modificara estados externos; los servicios V2 son la autoridad.

## Risks / Trade-offs

- [Servicios de cierre duplicados en V2] -> Seleccionar el runtime invocado por `api/index.py`, cubrirlo con pruebas de contrato y no ampliar el servicio legado no usado.
- [Datos existentes con origen incompleto] -> Migracion idempotente que inicialice seguimiento sin destruir semanas cerradas; marcar procedencia desconocida de forma trazable.
- [Reprogramacion concurrente] -> Transacciones, restriccion de unicidad y validacion de programaciones abiertas antes de cambiar estado.
- [Redisenio transversal provoca regresiones] -> Entrega por features, pruebas de componentes/contratos y verificacion visual de flujos principales en escritorio y ancho reducido.
- [Backlog crece con el tiempo] -> Indices por estado, especialidad, primer origen y OT; paginacion o limites si la consulta lo requiere.

## Migration Plan

1. Crear y validar una migracion V2 aditiva para campos/indices de seguimiento e inicializar los registros activos existentes sin editar migraciones aplicadas.
2. Implementar transiciones transaccionales de backlog en programacion y cierre, con endpoints de lectura y pruebas de ciclo completo.
3. Entregar el shell y Backlog nuevo junto con la navegacion desde Cierre; mantener los modulos actuales detras de los mismos contratos mientras se migra cada feature.
4. Ejecutar verificacion de schema, contrato, frontend, backend y regresion de capacidad antes de integrar.
5. Si es necesario revertir, desplegar la UI anterior y dejar los campos aditivos sin borrar historial; las transiciones nuevas no se revertiran mediante eliminacion de datos.
