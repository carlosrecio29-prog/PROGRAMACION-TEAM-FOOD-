# Ciclo de importación

Las entradas actuales son XLSX procesados por `backend/parsers/` y cargados por servicios V1/V2; se registra metadata de importación y no se conserva el archivo completo. El objetivo es: validar → normalizar → persistir batch → actualizar sólo entidades fuente → preservar complementos e historial. El importador V2 actual contiene un `TRUNCATE ... CASCADE`, riesgo crítico que requiere cambio separado. La política de reimportación e historial por batch debe especificarse antes de corregirlo.
