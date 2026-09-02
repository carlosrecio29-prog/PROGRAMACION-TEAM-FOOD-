ALTER TABLE programacion.activo
  ADD COLUMN IF NOT EXISTS area_codigo text
  GENERATED ALWAYS AS (
    CASE
      WHEN codigo LIKE 'BA-%' THEN split_part(codigo,'-',2)
      ELSE NULL
    END
  ) STORED;

CREATE INDEX IF NOT EXISTS idx_activo_area_codigo
  ON programacion.activo(area_codigo);

COMMENT ON COLUMN programacion.activo.area_codigo IS
  'Área inferida automáticamente del código del equipo. Ejemplo BA-EM-X-X-X -> EM. No reemplaza la ubicación física específica.';
