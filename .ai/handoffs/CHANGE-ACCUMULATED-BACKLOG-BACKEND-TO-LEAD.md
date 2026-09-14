# Handoff: accumulated backlog V2 — backend/runtime

- Change ID: `redesign-platform-ux-and-accumulated-backlog`
- Active API runtime: `api/index.py` → `backend.services.v2_programming_runtime` and `backend.services.v2_closure_service`.
- Candidate source: `programacion.orden_mantenimiento` joined to `activo` and `plan_trabajo`; weekly lookup filters `o.especialidad`, monthly `periodo`, non-finalized state and complete effective plan fields.
- Backlog source: `programacion.backlog_v2`; active lifecycle fields are added by `supabase/migrations_v2/20260913235500_add_accumulated_backlog_tracking_v2.sql`.
- Closure authority: `v2_closure_service.close_week_from_calendar`; pending/no-match rows stay active, finalized rows are closed in backlog.
- Frontend contract: `frontend/src/api.js` calls `/api/v2/programming/week` and `/api/v2/backlog`; `WeeklyClosure` opens Backlog with `order_id` context.
- Current blocker: this workspace has no `DATABASE_URL`, Supabase CLI, or connected database. A deployed 500 from both programming and backlog is consistent with the active migration not being applied to the target database. Apply the complete V2 migration chain, then verify the MEC week request (`specialty=MEC`) and backlog request before release.
- Regression fixed in this slice: no-match closure now records `ultimo_resultado_cierre='NO_ENCONTRADA'` instead of incorrectly recording `PENDIENTE`.
- Verification: `python -m pytest -q` passed (10 tests); Python compilation passed. Remote schema/MEC integration remains unverified.
