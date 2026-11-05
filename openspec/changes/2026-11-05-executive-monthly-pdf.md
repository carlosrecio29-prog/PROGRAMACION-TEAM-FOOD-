# Informe gerencial de cierre mensual - diseño corporativo C.E.K / Team Foods

## Intención
Al descargar el PDF desde **Cierre mensual** se genera un informe en A4
vertical inspirado visualmente en el PDF corporativo de referencia compartido
por el usuario (portada con identidad C.E.K, geometría azul, secciones numeradas,
KPI de lectura rápida, tablas y conclusiones). El contenido no se copia del
informe de criticidad utilizado como referencia: se extrae exclusivamente de
los registros del cierre/seguimiento mensual en la plataforma.

## Datos y trazabilidad
- Mantener la ruta actual `/api/v2/progress/report.pdf?year=&month=`
  como lectura, sin introducir cambios de BD ni de estados de órdenes.
- Las OT generales de la cartera son únicas: suma de
  `monthly_progress_by_specialty.total_ot`, finalizadas y H-H estimadas.
- Se muestran OT programadas únicas y finalizadas sin duplicar asignaciones
  semanales; las OT fuera de programación se informan por separado.
- Las barras semanales representan **eventos de asignación**, explícitamente
  diferenciados del universo de OT únicas.
- Backlog y pendientes se declaran por su criterio disponible:
  heredadas, pendientes del último cierre, PMP sin programar y no encontradas
  no se suman ni se presentan como el saldo total de la BD.
- H-H son estimadas del plan; nunca afirmar que son horas reales.
- Si faltan cierres semanales se marca **INFORME PARCIAL**.
- Las recomendaciones se etiquetan como sugerencias, sin declarar aprobación.
- Fecha de emisión y código de reporte se generan automáticamente.
- El PDF semanal conserva su formato anterior y su nombre de archivo.

## Secciones
1. Portada corporativa.
2. Resumen ejecutivo.
3. Balance mensual de OT.
4. Evolución semanal.
5. Desempeño por especialidad.
6. Backlog y desviaciones.
7. Conclusiones, recomendaciones y trazabilidad.

## Verificación
Probar con y sin datos por especialidad; con cierres parciales; con varias
semanas y con filas de pendientes. Comprobar 7 páginas A4, tablas sin
desbordamientos, logos, percentiles coherentes y ninguna mutación de datos.
