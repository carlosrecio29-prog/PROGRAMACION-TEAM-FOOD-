# Reportes de cierre semanal y mensual — PROGRAMACIÓN TEAM FOOD

## Alcance
- La sección Resumen operativo consulta cierres V2 existentes sin reimportar Excel.
- Menú Cierre > Informe mensual ofrece consolidado del mes y PDF.
- Cierre semanal muestra botón PDF solo después de estado CERRADA.
- GET /api/v2/progress?year=2026&month=9 retorna weeks, specialties, weekly_totals, monthly, unresolved y criteria.
- GET /api/v2/progress/report.pdf?year=2026&month=9[&programming_id=N] produce PDF mensual o semanal. Solo lectura.

## Invariantes
- Semana = jueves a miércoles, con la fecha de inicio asignando la programación al periodo seleccionado.
- Contadores semanales y HH suman eventos programados; una OT recuperada de backlog puede aparecer en varias semanas.
- Contadores mensuales de OT distintas deduplican por orden_mantenimiento_id y utilizan el cierre de la última semana en el periodo.
- El conteo del PMP incluye OT de mantenimiento del mes aún no programadas; excluir planes OPERACIÓN.
- HH finalizadas = HH estimadas de la programación para OT finalizadas, no HH reales de ejecución.
- Programaciones GUARDADAS no se toman por cierres; marcar documento PARCIAL si existen semanas sin cerrar.
- OT sin encontrar se diferencian de OT pendientes y del universo no programado.
- No modificar estados, programación, backlog, migraciones ni cargas Excel para generar avances o PDF.

## QA
- Prueba de una OT abierta y luego finalizada tras reprogramarse: dos eventos, una OT única finalizada.
- Prueba de mes con semana no cerrada: no se inventa cumplimiento.
- Filtro de especialidad afecta las tablas/gráficos semanales, no cambia las cifras globales del mes.
- Descarga de PDF se calcula bajo demanda desde la misma consulta que alimenta el dashboard.
