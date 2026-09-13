# Handoff

- Change ID: reorganize-frontend-weekly-programming-ux
- Agent/role: Lead → QA / Frontend review
- Objective: Improve the V2 weekly-programming UX without changing backend contracts or domain rules.
- Files modified: `frontend/src/App.jsx`, `frontend/src/components/WeeklyProgramming.jsx`, `frontend/src/features/planning/weeklyProgrammingFilters.js`, `frontend/src/features/planning/weeklyProgrammingSelection.js`, `frontend/src/backlog.css`, `frontend/tests/weeklyProgrammingFilters.test.mjs`, OpenSpec tasks.
- Contracts created/changed: New frontend UX contract in `openspec/changes/reorganize-frontend-weekly-programming-ux/specs/frontend/weekly-programming-ux/spec.md`; V2 API payloads remain unchanged.
- Migrations created: None.
- Tests added: Four Node tests for independent filters, filter persistence, immutable selection/removal, and capacity-limit rejection.
- Tests executed/results: `python -m pytest -q` — 10 passed; `node --test frontend/tests/weeklyProgrammingFilters.test.mjs` — 4 passed; `npm run build` — passed; destructive and ownership checks — passed.
- Unresolved assumptions: The backend endpoint still supplies its existing `created_by` default; the new frontend no longer sends a hardcoded actor. Full actor identity remains a separate V2 concern.
- Known risks: Visual regression and live scroll behavior need a browser-connected QA pass; this environment had no available browser surface and `agent-browser` was not installed.
- Follow-up work: Verify desktop and mobile layouts for Programación semanal; test selection and removal after scrolling inside each activity table; review Resumen, Cierre semanal and PMP for CSS regressions.
- Ownership requested: QA / Frontend to complete OpenSpec tasks 4.3 and 5.4 using a connected browser.
- Destructive-change review required: No; guard passed.
