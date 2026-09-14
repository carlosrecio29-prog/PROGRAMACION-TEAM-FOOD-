---
name: team-food-security-release
description: Review TEAM FOOD security, CI, dependencies, deployment configuration, and release readiness.
---

# TEAM FOOD Security / Release Skill

Use for CI, dependency manifests, Vercel/Supabase release configuration, secrets, auth/RLS, and go/no-go review. Set `AGENT_ROLE=security-release` for ownership checks.

Confirm service-role keys stay server-side, review actor/auth/RLS/CORS and reproducibility, and require verification, ownership, and destructive-change evidence. Do not deploy when tests, migration checks, or safety guards fail; prefer preview/staging. Escalate domain/schema edits to the owning agent.

Detailed role profile: [security-release.agent.md](../../agents/security-release.agent.md).
