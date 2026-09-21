# Exclusión de planes delegados a OPERACIÓN (21/09/2026)

## Decisión de dominio
Una actividad se considera delegada a OPERACIÓN cuando el nombre PlanTrabajo comienza por OPERACIÓN (también OPERACION sin tilde), con un prefijo numérico opcional como `12-OPERACIÓN`. La palabra en otra posición no excluye. La identificación se hace por clave de plan (Grupo + PlanTrabajo) y queda persistida en `programacion.plan_trabajo.es_operacion`.

## Contrato
- Cargar el maestro de planes sin reimportar los otros libros: POST `/api/v2/import-operation-master` con multipart `plans`. Devuelve los totales y el detalle de los planes de OPERACIÓN.
- Cargar cada Lista de Calendario: POST `/api/v2/import-monthly-calendar?year=YYYY&month=MM` con multipart `monthly`. Devuelve total de registros, excluidos por OPERACIÓN, importados/actualizados, advertencias y totales existentes por período.
- Carga inicial de los tres libros mantiene su ruta existente e informa `pmp_excluidos_operacion`.
- No borramos historial, cierres, programaciones, complementos ni backlog. Las órdenes históricas clasificadas de OPERACIÓN dejan de aparecer en PMP/pendientes/candidatos/backlog activos; el guardado de programación rechaza sus IDs.
- `TiempoParada=0` sigue siendo un valor válido para equipo operando, sin relación con este filtro.

## Comprobaciones
Pruebas del parser para tilde, prefijo numérico y falsos positivos, pruebas estáticas del filtro backend y verificación de build/frontend y rutas. Validar posteriormente con archivos reales en despliegue.
