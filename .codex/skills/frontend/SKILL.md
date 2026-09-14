---
name: team-food-frontend
description: Build TEAM FOOD React/Vite UI and API consumption without duplicating domain calculations.
---

# TEAM FOOD Frontend Skill

Use for `frontend/**`. Set `AGENT_ROLE=frontend` for ownership checks. Read the OpenSpec and API handoff before changing screens or payloads.

Treat backend responses as authoritative: never recalculate HH, capacity, canonical states, closure results, or eligibility rules in React. Coordinate API changes with Backend, modularize `App.jsx` gradually, keep secrets out of the browser, and cover loading, empty, failure, stale/closed-week, and success states.

Run frontend build/tests and report contract mismatches instead of hiding them in client logic.

Detailed role profile: [frontend.agent.md](../../agents/frontend.agent.md).
