CREATE TABLE IF NOT EXISTS programacion.backlog_v2 (
    id bigserial PRIMARY KEY,
    orden_mantenimiento_id bigint NOT NULL REFERENCES programacion.orden_mantenimiento(id) ON DELETE CASCADE,
    programacion_origen_id bigint REFERENCES programacion.programacion_semanal_v2(id) ON DELETE SET NULL,
    semana_origen_inicio date NOT NULL,
    semana_origen_fin date NOT NULL,
    especialidad varchar(10) NOT NULL,
    motivo text,
    movido_por text,
    movido_en timestamptz NOT NULL DEFAULT now(),
    actualizado_en timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT backlog_v2_orden_unique UNIQUE (orden_mantenimiento_id)
);

CREATE INDEX IF NOT EXISTS ix_backlog_v2_especialidad
    ON programacion.backlog_v2(especialidad, movido_en DESC);

CREATE INDEX IF NOT EXISTS ix_backlog_v2_semana_origen
    ON programacion.backlog_v2(semana_origen_inicio, semana_origen_fin);

COMMENT ON TABLE programacion.backlog_v2 IS
'OT retiradas de una programación semanal guardada para tenerlas visibles y priorizarlas en semanas posteriores.';
