# Sincronización diaria y manual de Google Sheets — CEK Global MTTO

## Fuente de verdad
- Libro `1Or0L7epumDQUsUuLjb4FXt-7FRbC16pJ8-b0VwROwdo`.
- **Solo** pestaña `BASE DE DATOS`, rango A:M. No se lee el selector de mes de las pestañas individuales.
- Se toman MES, # DE ORDEN, ESPECIALIDAD, CÓDIGO, ESTADO, PLAN DE TRABAJO, TIEMPO y metadatos. FECHA PROG no equivale a fecha real de finalización.
- Cuenta de servicio con permiso lector en Google Sheets; credenciales exclusivamente del lado servidor.

## Decisiones
1. Plan prefijado por código + OPERACIÓN se excluye de programación e indicadores y se registra aparte.
2. La identidad es `numero_ot` normalizado; una OT repetida idéntica no se duplica, contradicciones quedan para revisión.
3. Una OT previa reutilizada en el mes no se vuelve a crear; si está pendiente y sin backlog, se concilia.
4. Estados de origen `FINALIZADA` y `FINALIZADO` equivalen a `FINALIZADA`. Estados regresivos respecto de finalizado/anulado se dejan como conflicto.
5. Se actualizan estados de órdenes abiertas del período y fotografías de **seguimiento provisional de la semana activa**. No se modifica ninguna asignación, H-H guardada, programación semanal cerrada ni cierre mensual histórico.
6. La fecha de detección no se presenta como fecha real de cierre. El cierre formal sigue siendo una operación explícita del usuario.
7. Se crea una bitácora inmutable de ejecuciones, cambios de estado y conflictos. Faltantes o errores de Google no provocan bajas automáticas.
8. Los nuevos planes o equipos no verificables se reportan y no se inventan. Para activos con código BA- válido y plan conocido puede completarse el maestro desde la fila.
9. Noviembre de 2026 es el primer mes sincronizable; octubre y meses previos quedan protegidos.
10. Una sola rutina se ejecuta por botón o Vercel Cron. Cron: `0 11 * * *` UTC, equivalente a 06:00 de Colombia.

## Contrato API
- `GET /api/v2/sheet-sync/status?year=2026&month=11` (solo administrador): configuración y última ejecución.
- `POST /api/v2/sheet-sync?year=2026&month=11` (sesión admin): inicia conciliación.
- `GET /api/v2/sheet-sync/cron` (solo header `Authorization: Bearer CRON_SECRET`): inicia conciliación del mes actual.

## Requisitos de despliegue
- API de Google Sheets habilitada en el proyecto GCP.
- Cuenta de servicio compartida como *lector* del documento.
- Variable cifrada `GOOGLE_SHEETS_SERVICE_ACCOUNT_JSON` con el JSON de credenciales en Vercel, **no en GitHub ni en el frontend**.
- Variable cifrada `CRON_SECRET` con un valor aleatorio robusto en Vercel.
- Migration `20261109153000_google_sheet_sync_v2.sql` aplicada antes de activar la rutina.
- Verificar primera ejecución manual, después la diaria, y comparar los indicadores con los de octubre.

## Pruebas de aceptación
- Un cambio PENDIENTE→FINALIZADA de una OT de noviembre modifica el avance mensual y el seguimiento actual, sin reescribir el cierre.
- Dos filas idénticas de una OT se deduplican; filas contradictorias no mutan esa OT.
- Las actividades OPERACIÓN continúan aparte.
- No se eliminan programaciones ni H-H guardadas al refrescar.
- Un cierre confirmado en octubre permanece intacto y ningún mes anterior a noviembre es sincronizable.
- La ausencia de la credencial produce un error controlado y no ejecuta actualizaciones parciales.
