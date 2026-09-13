# ADR-002: Política de migraciones

Status: Accepted

## Decision
`supabase/migrations_v2/` es la cadena activa; `supabase/migrations/` es histórico V1. Las migraciones aplicadas son inmutables. Cambios nuevos son aditivos y requieren prueba en base fresca y, cuando sea posible, con datos existentes. Operaciones destructivas necesitan la política de `.ai/destructive-change-policy.md`.
