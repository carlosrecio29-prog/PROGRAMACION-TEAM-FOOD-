# TEAM FOOD — Constitución de ingeniería

## Límite del producto

TEAM FOOD es una capa de planeación y conciliación sobre un sistema externo de mantenimiento. El sistema externo es la fuente de verdad para activos, planes, OT/PMP, técnicos, turnos y estados importados. TEAM FOOD es dueño de complementos manuales, capacidad calculada, programación semanal, backlog, cierres, reportes e historial de decisiones.

## Arquitectura actual

- V2 es el runtime activo: `api/index.py`, `backend/services/v2_*.py`, `frontend/src/` y `supabase/migrations_v2/`.
- V1 es legado: `backend/services/{import_service,programming_service,query_service,team_food_service}.py`, `backend/services/definition_service.py` y `supabase/migrations/`. No agregar funcionalidad nueva allí.
- Backend: FastAPI, parsers Excel y servicios SQLAlchemy; frontend: React/Vite; base: PostgreSQL/Supabase; despliegue: Vercel.
- Las migraciones V2 son la cadena activa. Las migraciones antiguas son referencia histórica y no deben reaplicarse.

La arquitectura verificable y los riesgos están en `.ai/architecture.md`; las reglas de dominio están en `openspec/specs/` y `.ai/invariants.md`.

## Reglas obligatorias

1. No agregar funcionalidades a V1 ni crear migraciones V1.
2. Nunca editar una migración ya aplicada; todo cambio de esquema usa un archivo nuevo.
3. Un import nunca puede borrar programación o cierres históricos. Los complementos de aplicación sobreviven una reimportación.
4. No introducir `TRUNCATE`, `DROP`, `CASCADE`, DELETE amplio o reemplazos irreversibles sin revisión explícita según `.ai/destructive-change-policy.md`.
5. Estados externos se normalizan a conceptos canónicos; `FINALIZADA` y `FINALIZADO` son finalizados.
6. La fórmula HH y la capacidad tienen una sola autoridad de dominio/backend. El frontend muestra resultados y no los recalcula.
7. Toda mutación nueva debe prepararse para identidad de actor y auditoría; no crear usuarios hardcodeados.
8. Cambios de comportamiento requieren pruebas. Cambios de API requieren especificación/contrato antes de divergir frontend y backend.
9. Respeta `.ai/ownership.yaml`. Si necesitas otro dominio, registra un handoff o pide transferencia al Lead.
10. Nunca expongas claves service-role al frontend ni hagas cambios de producción no verificados.
11. Usa los agentes y asigna tasks a ellos que estan en .codex

## Flujo de trabajo

Request → dominio e invariantes → especificación OpenSpec → modelo/API → dependencias → implementación aislada → QA → Release. Usa `.ai/workflow.md`, crea una rama/worktree por tarea y deja `.ai/handoffs/` cuando cruces dominios o entregues trabajo.

Antes de codificar: identifica ambigüedades y escríbelas como decisión pendiente, no inventes una regla. El Lead coordina contratos y conflictos; especialistas trabajan sólo en su ownership.

## Verificación e integración

Ejecuta `bash scripts/verify.sh` (o cada script individual). También ejecuta `python scripts/check_agent_ownership.py` y `python scripts/check_destructive_changes.py`. CI es el árbitro final. El Lead integra en orden: migración/contrato, backend y frontend, QA, release.
