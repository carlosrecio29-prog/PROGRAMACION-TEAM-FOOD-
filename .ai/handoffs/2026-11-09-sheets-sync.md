# Handoff: sincronización BASE DE DATOS → CEK Global MTTO

**Lead / alcance:** backend FastAPI (`v2_sheet_sync_service.py` y rutas), UI Seguimiento semanal, migración V2, deploy Vercel y pruebas de regresión.

**Invariantes obligatorias:** INV-001, INV-002, INV-004, INV-006, INV-010, INV-011, INV-012 de `.ai/invariants.md`. No editar V1 ni reescribir los cierres de octubre.

**Backend:** Google Sheets API de solo lectura, idempotencia de OT, no permitir retrocesos automáticos, semana activa solamente para fotografías de seguimiento, respuesta auditada.

**Database:** tres tablas privadas en esquema programacion para ejecución, último estado observado y auditoría. No eliminar ni modificar tablas históricas. Aplicar migración antes de desplegar.

**Frontend:** botón solo administrador; mostrar última ejecución y errores de configuración sin credenciales.

**Security / release:** `GOOGLE_SHEETS_SERVICE_ACCOUNT_JSON` y `CRON_SECRET` son requeridas en Vercel y deben configurarse fuera de GitHub. Endpoint cron autenticado. En ausencia de claves no ejecutar mutaciones. El cron usa las 11:00 UTC diarias.

**QA:** casos puros de parser, duplicados, estado y OPERACIÓN; pruebas sobre datos reales con estado de cuenta de servicio antes de liberar.

**Pendiente de operación:** validación final con credenciales/permiso lector en proyecto de Vercel; no existe traslado automático de la sesión Google Drive de ChatGPT a las funciones serverless.
