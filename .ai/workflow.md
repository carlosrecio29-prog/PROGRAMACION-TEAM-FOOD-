# Trabajo multiagente

El Lead crea `change/team-food-<id>` y, cuando sea posible, worktrees separados: `agent/db-<id>`, `agent/backend-<id>`, `agent/frontend-<id>`, `agent/qa-<id>`. Cada agente declara `AGENT_ROLE` y entrega un handoff.

Primero se estabilizan invariantes, esquema y contrato API. Luego DB → contrato → backend/frontend en paralelo → QA/integración → Release. No lanzar todos los agentes a la vez: los archivos compartidos y las migraciones son dependencias secuenciales.

El Lead revisa conflictos, integra commits pequeños y ejecuta todos los gates. Una rama que cambia schema no se integra antes de probar migración fresca y sobre datos representativos.
