# Cumplimiento sobre OT únicas programadas del mes

## Problema
En el consolidado de cierre se mostraban 298 de 646 "registros de programación",
con el porcentaje 46,1 %. El denominador sumaba una fila por asignación en
cada semana, incluyendo la misma OT arrastrada a semanas posteriores. Eso no
equivale a 646 órdenes de trabajo diferentes.

## Contrato de indicadores

- **Cumplimiento mensual general:** `completed_ot / total_ot` de
  `monthly_progress_by_specialty`; cartera PMP + backlog, OT únicas.
  Incluye OT finalizadas fuera de programación.
- **Cumplimiento de OT programadas únicas:** `scheduled_completed /
  scheduled_unique`, campos calculados y servidos por backend en
  `monthly_progress_by_specialty`. `scheduled_unique` usa
  `COUNT(DISTINCT programacion_item_v2.orden_mantenimiento_id)` de
  programaciones cuya semana inicia dentro del mes; excluye planes OPERACIÓN.
- **Control de reprogramaciones:** `scheduled_assignments` suma filas
  semanales (puede contar la misma OT más de una vez);
  `scheduled_reprogrammed_assignments` = diferencia frente a
  `scheduled_unique`, solo informativo, no denominador del cumplimiento.
- Para semanas y OT abiertas, se conserva la lógica de la fuente vigente del
  indicador mensual. El objetivo es eliminar la duplicación del denominador,
  no alterar decisiones de seguimiento, cierre, backlog ni H-H.

### Caso verificado (octubre de 2026, Eléctrica)
- General: 410 / 479 = 85,6 %.
- Programadas únicas: 298 / 357 = 83,5 %.
- Asignaciones semanales: 646 (289 adicionales por reprogramación).

## Alcance
Cambios de consulta y presentación de KPIs. Ninguna mutación en tablas,
reimportación de OT, ajuste de cierres ni migración.
