-- Sincronización de estados desde BASE DE DATOS; no modifica tablas de cierres.
-- Tablas privadas del esquema programacion, sin GRANT para anon/authenticated.
CREATE TABLE IF NOT EXISTS programacion.google_sheet_sync_run_v2 (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 periodo date NOT NULL,
 origen text NOT NULL CHECK (origen IN ('CRON','MANUAL')),
 estado text NOT NULL CHECK (estado IN ('COMPLETADA','ERROR','OMITIDA')),
 iniciado_en timestamptz NOT NULL DEFAULT now(),
 terminado_en timestamptz NOT NULL DEFAULT now(),
 filas_leidas integer NOT NULL DEFAULT 0,
 ots_validas integer NOT NULL DEFAULT 0,
 ots_nuevas integer NOT NULL DEFAULT 0,
 estados_cambiados integer NOT NULL DEFAULT 0,
 backlog_conciliado integer NOT NULL DEFAULT 0,
 exclusiones_operacion integer NOT NULL DEFAULT 0,
 seguimientos_actualizados integer NOT NULL DEFAULT 0,
 conflictos integer NOT NULL DEFAULT 0,
 resumen jsonb NOT NULL DEFAULT '{}'::jsonb,
 error_resumido text
);
CREATE INDEX IF NOT EXISTS google_sheet_sync_run_period_idx
  ON programacion.google_sheet_sync_run_v2(periodo,iniciado_en DESC);

CREATE TABLE IF NOT EXISTS programacion.google_sheet_ot_estado_v2 (
 periodo date NOT NULL,
 numero_ot text NOT NULL,
 especialidad varchar(10) NOT NULL,
 estado text NOT NULL,
 plan_trabajo text,
 activo_codigo text,
 es_operacion boolean NOT NULL DEFAULT false,
 hoja_fila integer,
 observado_en timestamptz NOT NULL DEFAULT now(),
 actualizado_en timestamptz NOT NULL DEFAULT now(),
 ultima_sincronizacion_id bigint REFERENCES programacion.google_sheet_sync_run_v2(id),
 PRIMARY KEY(periodo,numero_ot)
);
CREATE INDEX IF NOT EXISTS google_sheet_ot_estado_v2_state_idx
  ON programacion.google_sheet_ot_estado_v2(periodo,especialidad,estado);

CREATE TABLE IF NOT EXISTS programacion.google_sheet_sync_cambio_v2 (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 sincronizacion_id bigint NOT NULL REFERENCES programacion.google_sheet_sync_run_v2(id),
 periodo date NOT NULL,
 numero_ot text NOT NULL,
 orden_mantenimiento_id bigint REFERENCES programacion.orden_mantenimiento(id),
 accion text NOT NULL,
 estado_anterior text,
 estado_nuevo text,
 detalle text,
 registrado_en timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS google_sheet_sync_cambio_run_idx
  ON programacion.google_sheet_sync_cambio_v2(sincronizacion_id);
