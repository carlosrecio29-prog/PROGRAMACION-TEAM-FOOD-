# Handoff

- Change ID: CHANGE-001-nondestructive-v2-import
- Agent/role: Backend → QA, coordinated by Lead
- Objective: Reconcile V2 source snapshots without deleting TEAM FOOD history or complements.
- Files modified: `backend/services/v2_import_service.py`, `tests/test_v2_import_safety.py`, OpenSpec change.
- Contracts created/changed: Import identity and source/app-owned lifecycle documented in OpenSpec.
- Migrations created: None; existing V2 unique constraints are sufficient for this slice.
- Tests added: Four safety/identity tests derived from acceptance scenarios.
- Tests executed/results: `py -m pytest -q` — 10 passed; full `bash scripts/verify.sh` — passed.
- Unresolved assumptions: PostgreSQL lifecycle tests still require an integration database; order numbers are assumed stable within a monthly period; raw `(grupo, plan_trabajo)` uniqueness remains the current plan key.
- Known risks: Existing deployed data must be tested before rollout; duplicate historical rows from previous resets cannot be recovered by this change.
- Follow-up work: Add real PostgreSQL lifecycle tests and import-batch metadata if the current import record is insufficient.
- Ownership requested: QA to validate A–G lifecycle scenarios against representative existing data; Database/Security to approve production rollout.
- Destructive-change review required: no new destructive operation; guard passed.
