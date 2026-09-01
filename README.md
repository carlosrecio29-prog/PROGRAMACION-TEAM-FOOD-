# PROGRAMACION TEAM FOOD

Programador semanal de mantenimiento refactorizado a:

- **React + Vite** para el frontend.
- **FastAPI / Python** para API y parsers de Excel.
- **PostgreSQL en Supabase** como única fuente de verdad.
- **Vercel** para frontend + FastAPI serverless.
- **Supabase migrations** versionadas en Git.

## Arquitectura

```text
Excel XLSX
   ↓ upload temporal
FastAPI parser
   ↓ validación + normalización
PostgreSQL / Supabase
   ↓
FastAPI queries
   ↓
React
```

Los XLSX **no se guardan completos**. Solo se conserva en `mantenimiento.importacion` la metadata, métricas de carga y errores.

## CI/CD
Cada push a `main` ejecutará tests, build, migraciones Supabase y despliegue en Vercel.