# Preparación anticipada de paradas del próximo mes

## Flujo
- Menú Planificación > Preparación de paradas, independiente del PMP operativo.
- El usuario elige año y mes a preparar; valor inicial: mes siguiente al de programación seleccionado.
- Al adjuntar Lista de Calendario XLSX se analiza automáticamente. Número de OT/Orden opcional.
- Clasificación basada en plan de trabajo del maestro actual, coincidiendo Grupo-PlanTrabajo (como el importador existente):
  - TiempoParada efectivo > 0: EQUIPO DETENIDO.
  - TiempoParada efectivo = 0: OPERANDO.
  - TiempoParada sin definir o plan sin maestro: SIN DEFINIR y observación de revisión.
  - Planes es_operacion: fuera del listado de mantenimiento, con contador de excluidos.
- Equipo no encontrado: indicar observación, no inventar descripción o criticidad.
- Una fila del calendario provisional representa una actividad incluso sin número de OT.
- Mostrar contadores, filtro de condición, especialidad y búsqueda; exportar **todas las filas** independientemente del filtro en pantalla.
- Exportar Excel con RESUMEN, EQUIPO DETENIDO, OPERANDO, SIN DEFINIR. Incluir equipo, área, criticidad, especialidad, OT opcional, plan, tiempos, personas, HH estimadas, origen y observaciones. Columnas amarillas editables para que el planeador coordine fecha, ventana, responsable y estado.
- El mes seleccionado etiqueta el entregable; no atribuir fecha específica de parada si no está documentada en el Excel.
- Los Excel se procesan temporalmente; preview/export son SOLO LECTURA, sin INSERT, UPDATE o DELETE de OT/PMP, programación, backlog y cierres.
- Endpoint POST /api/v2/advance-stops/preview, multipart monthly + year/month.
- Endpoint POST /api/v2/advance-stops/export.xlsx, mismo archivo y período, devuelve XLSX.

## QA
- Exportación del calendario sin columna Orden.
- TiempoParada = 0 no es SIN DEFINIR.
- TiempoParada ausente no es OPERANDO.
- Un plan no encontrado se reporta SIN DEFINIR.
- OPERACIÓN excluido.
- Los períodos diciembre→enero funcionan.
- El XLSX descargado contiene todas las pestañas y filas, aunque la página limite filas visibles.
