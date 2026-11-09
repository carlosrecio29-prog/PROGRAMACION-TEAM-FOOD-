# CEK Global MTTO · Sincronización Google Apps Script sin Google Cloud

## Alcance aprobado
- Fuente única: pestaña **BASE DE DATOS** del libro
  https://docs.google.com/spreadsheets/d/1Or0L7epumDQUsUuLjb4FXt-7FRbC16pJ8-b0VwROwdo/edit.
- Origen de estados: Google Sheets, no el selector de las hojas de especialidades.
- Destino: Supabase mediante backend FastAPI/Vercel.
- Sin tarjeta, sin crear proyectos Google Cloud, sin cuenta de servicio.
- Modo B: actualización automática diaria en torno a las **06:00 America/Bogota** y botón de sincronización adicional para administrador.
- Backlog, H-H de programación, semanas cerradas y cierre mensual son propiedad de CEK Global MTTO y permanecen protegidos.

## Arquitectura
1. Apps Script ligado al documento de Google Sheets lee exclusivamente `BASE DE DATOS!A:M`, filtra el mes por columna MES y conserva el número original de fila en metadatos de transporte.
2. Trigger de reloj de Apps Script (`cekSincronizacionDiaria`) realiza POST al endpoint protegido `/api/v2/sheet-sync/push` con datos actuales del mes. Apps Script se ejecuta con autorización del propietario del documento.
3. El botón **Sincronizar ahora** de CEK Global MTTO realiza POST admin a `/api/v2/sheet-sync`, que consulta el Web App Apps Script mediante POST con secreto en el **cuerpo HTTPS**.
4. Ambos canales ejecutan la misma rutina `sync_month`, transaccional e idempotente, con bloqueo advisory y auditoría en esquema privado `programacion`.
5. Apps Script Web App `doPost` requiere un secreto largo. `doGet` no expone datos.

## Seguridad
- El Google Sheets queda privado; **no** habilitar «Cualquiera con el enlace» en el documento original.
- El Web App de Apps Script se despliega *Ejecutar como: Yo* y *Quién tiene acceso: Cualquier persona*, para aceptar solicitudes de servidor Vercel. El Web App verifica un secreto aleatorio de 32+ caracteres antes de devolver cualquier dato.
- Propiedad privada de Apps Script: `SHEET_SYNC_SECRET` y `CEK_API_URL`.
- Variables de entorno privadas de Vercel: `SHEET_SYNC_SECRET` (idéntico) y `APPS_SCRIPT_WEBAPP_URL` (URL `https://script.google.com/macros/s/.../exec`).
- El secreto nunca se incorpora a código fuente, query string, frontend ni respuesta de estado.
- `/api/v2/sheet-sync/push` requiere Authorization: Bearer y admite solo el mes actual.
- `/api/v2/sheet-sync` exige sesión de administrador; `/api/v2/sheet-sync/status` exige rol administrador.
- Requiere configurar manualmente las variables y autorizar el script desde la cuenta Google del usuario; ChatGPT no puede transferir su autorización de Google Drive a Vercel.

## Reglas de negocio
- Normalizar `FINALIZADA`/`FINALIZADO` como finalizado, `ANULADA` como anulada, `ABIERTO`/`PENDIENTE` como pendiente.
- OT por número normalizado. Filas repetidas idénticas se deduplican. Repeticiones contradictorias no se aplican y quedan para revisión.
- Prefijo `OPERACIÓN` (después del identificador numérico de plan) se excluye del universo de programación, se registra en exclusiones y no se elimina de Google.
- Horas programadas, selección de OT, responsables y cierre oficial **no se modifican**.
- Sólo sincronizar la semana activa si aún no está cerrada. Sin fecha real de finalización no se asigna una fecha inventada; se conserva fecha de observación.
- Una OT que haya terminado y esté cerrada no retrocede a pendiente. Cierres de octubre anteriores a 2026-11-01 nunca se sincronizan; meses cerrados tampoco.
- No eliminar registros ausentes en la foto más reciente; problemas de Google o listas incompletas producen error transaccional y no actualizaciones parciales.
- Auditoría de cada ejecución (`google_sheet_sync_run_v2`), cambios por OT (`google_sheet_sync_cambio_v2`) y estado fuente (`google_sheet_ot_estado_v2`).

## Operación / límites
- Programa Apps Script diario cerca de 06:00 Colombia; los activadores de tiempo no garantizan minuto exacto (Google tolera aproximadamente ±15 min).
- El botón manual hace pull a Apps Script. La rutina diaria hace push desde Apps Script; no hay Vercel Cron.
- Mantener la subida manual de Lista de Calendario .xlsx como respaldo.
- Validar primer push y primer pull en noviembre con cierres de octubre inalterados.

## Contratos
- `GET /api/v2/sheet-sync/status?year=2026&month=11`: admin, historial y estado de configuración sin secretos.
- `POST /api/v2/sheet-sync?year=2026&month=11`: admin, snapshot Apps Script + conciliación.
- `POST /api/v2/sheet-sync/push`: autorización por secreto, body JSON `{year,month,values}`; solo mes actual.

## Setup
Ver `scripts/google_apps_script/README.md`.
