-- Registro acumulativo e idempotente de OT del PMP/backlog detectadas
-- como FINALIZADAS al actualizar la Lista de Calendario.
CREATE TABLE IF NOT EXISTS programacion.finalizaciones_detectadas_v2 (
  orden_mantenimiento_id bigint PRIMARY KEY
    REFERENCES programacion.orden_mantenimiento(id) ON DELETE CASCADE,
  periodo date NOT NULL,
  especialidad varchar(12) NOT NULL,
  fecha_fin_orden timestamp without time zone,
  programacion_origen_id bigint NOT NULL
    REFERENCES programacion.programacion_semanal_v2(id),
  seguimiento_origen_id bigint NOT NULL
    REFERENCES programacion.seguimiento_semanal_v2(id),
  primera_deteccion_en timestamp with time zone NOT NULL DEFAULT now(),
  ultima_deteccion_en timestamp with time zone NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS finalizaciones_detectadas_v2_periodo_esp_idx
  ON programacion.finalizaciones_detectadas_v2(periodo, especialidad, programacion_origen_id);
ALTER TABLE programacion.finalizaciones_detectadas_v2 ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON programacion.finalizaciones_detectadas_v2 FROM PUBLIC, anon, authenticated;
