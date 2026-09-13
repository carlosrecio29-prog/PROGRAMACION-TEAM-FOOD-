# Backlog de aceptación de alto valor

Estos escenarios son obligatorios para cambios de importación, programación, cierre o backlog:

1. **Preservación histórica** — Given import A, programación y cierre de semana; When se importa B; Then la programación y cierre anteriores siguen consultables.
2. **Estado final canónico** — Given una OT externa `FINALIZADA` o `FINALIZADO`; When se importa y se consultan candidatas; Then no aparece como candidata activa.
3. **Ciclo backlog** — Given una OT programada no completada; When se cierra la semana; Then entra en backlog, puede programarse la siguiente semana y desaparece del backlog activo al finalizarse y cerrarse.
4. **Supervivencia de complementos** — Given un complemento manual; When se reimporta su fuente; Then el complemento permanece.
5. **Semana cerrada** — Given una semana cerrada; When una mutación normal intenta editarla; Then se rechaza y el cierre observado permanece intacto.

QA debe convertir cada escenario en pruebas de integración contra una base representativa antes de declarar consolidado el dominio.
