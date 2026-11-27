# Informe de cierre semanal: OT finalizadas fuera de programación

Fecha: 2026-11-27. Alcance: las cuatro especialidades, semanas de noviembre 2026 en adelante.

## Problema
La pantalla `Cierre semanal` únicamente leía la programación guardada y su cierre oficial. El indicador de primeras detecciones `FINALIZADA` que NO estaban en la programación estaba únicamente en `Seguimiento de programación`. El PDF de cierre semanal leía otra fuente histórica (`get_week_tracking().unplanned.rows`), que puede ser cero aun si el historial Google Sheets sí detectó finalizadas fuera de programación.

## Cambio
- En `WeeklyClosure.jsx`, cargar por especialidad y semana la misma consulta **read-only** `getWeeklyOutsideFinalizations` que usa Seguimiento.
- Añadir un único apartado específico de finalizadas fuera de programación, antes de las tarjetas de cumplimiento: total, programadas en otra semana, sin programación en el mes, detectadas después de corte, y tabla desplegable con OT, primera detección, programación previa, área, equipo y plan. Visible incluso cuando la programación está CERRADA.
- En `v2_progress_service.py`, consultar la misma auditoría semanal al descargar el PDF de cierre. En `v2_pdf_fallback.py`, renderizar **un único** bloque adicional basado en la auditoría. No confundir la fecha de detección con la fecha física de finalización ni inventar H-H para OT fuera de programación. Para períodos sin historial auditado, se conserva el bloque legado del PDF.
- No se modifican OT, programaciones, estados, cierres, H-H ni tablas de Supabase.
- Prueba en `tests/test_weekly_closure_outside_audit.py`.

## Verificación SQL (solo lectura)
Para la semana 3 (19–25 de noviembre 2026), la consulta actual de `weekly_finalized_outside_programming` devuelve: ELE 29, MEC 4, MET 6, SER 14; total 53, sin contar como ejecutadas programadas. Son primeras sincronizaciones que detectaron FINALIZADA, no fechas físicas de ejecución.

## Hallazgo temporal pendiente
Las nuevas sincronizaciones del **26/11 antes del cierre formal** detectaron 19 OT fuera de semana 3 de ELE y 4 de MEC. La semana 4 se guardó después del cierre de semana 3, pero la atribución actual prioriza la ventana calendario de semana 4 incluso para detecciones anteriores a su creación. La lógica de historial temporal requiere una decisión de dominio consistente porque en la semana 2 se fijó específicamente la prioridad de la semana calendario sobre la semana anterior, para evitar el recuento incorrecto reportado (68 ELE y 36 MEC en semana 2). No se modifica esta regla desde la tarea de visualización sin autorización y sin conciliación de todas las semanas. La nueva vista y PDF comparten un único cálculo para evitar dos cifras incompatibles dentro del mismo cierre. El cálculo operativo de primeras detecciones no debe presentarse como una verdad sobre la fecha física de los trabajos.
