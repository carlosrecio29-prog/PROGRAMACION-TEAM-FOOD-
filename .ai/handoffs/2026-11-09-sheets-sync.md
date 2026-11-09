# Handoff · Sync Google Apps Script (sin Google Cloud)

Repositorio: carlosrecio29-prog/PROGRAMACION-TEAM-FOOD-; PR #12.

- Backend: Google Apps Script fuente única BASE DE DATOS, canales manual pull y diario push.
- Segurança: `SHEET_SYNC_SECRET` mismo valor en Script Properties/Vercel; `APPS_SCRIPT_WEBAPP_URL` privado en Vercel; `CEK_API_URL` propiedad de Apps Script. El usuario configura sus propias credenciales, no compartir en chat.
- Frontend: botón admin e historial de sincronización, accesible desde Seguimiento de programación.
- Supabase: migration `20261109153000_google_sheet_sync_v2.sql` previamente aplicada y verificada. No tocar cierre mensual ni programación semanal aprobada.
- Release: verificar con primera ejecución manual y automática desde GAS antes de afirmar que la sincronización funciona; revisar conflictos, 4 especialidades, exclusiones OPERACIÓN, OT duplicadas, meses anteriores a noviembre y H-H guardadas.
- Docs: `scripts/google_apps_script/README.md`.
- Ownership cruzado (backend/frontend/db/QA/release) explícitamente registrado en este handoff.
