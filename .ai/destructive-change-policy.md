# Política de cambios destructivos

Por defecto, `scripts/check_destructive_changes.py` trata `TRUNCATE`, `DROP`, `CASCADE`, DELETE amplio, reemplazos masivos y edición de migraciones como revisión requerida o bloqueo. El detector es una señal de seguridad, no aprobación automática.

Para un cambio aprobado, el PR debe explicar alcance, datos afectados, respaldo, reversibilidad, migración fresca/existente y aprobación del Lead + database/security. El override temporal es `DESTRUCTIVE_CHANGE_APPROVED=1`; sólo debe usarse en CI/revisión con evidencia en el PR. Nunca pongas credenciales en el override ni lo conviertas en default.
