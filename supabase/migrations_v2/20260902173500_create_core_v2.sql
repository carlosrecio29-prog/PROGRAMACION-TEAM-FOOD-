CREATE SCHEMA IF NOT EXISTS programacion;

CREATE TABLE IF NOT EXISTS programacion.activo (
  id bigserial PRIMARY KEY,
  codigo text NOT NULL UNIQUE,
  descripcion text,
  activo_padre_codigo text,
  marca text,
  modelo text,
  serie text,
  ubicacion text,
  criticidad varchar(1),
  especialidad varchar(20),
  departamento text,
  centro_costo text,
  agrupacion text,
  grupo_analisis text,
  grupo_pdt text,
  estado text,
  habilitado boolean NOT NULL DEFAULT true,
  fila_origen integer,
  actualizado_en timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT activo_criticidad_check CHECK (criticidad IS NULL OR criticidad IN ('A','B','C'))
);

CREATE TABLE IF NOT EXISTS programacion.plan_trabajo (
  id bigserial PRIMARY KEY,
  grupo text NOT NULL,
  descripcion_grupo text,
  plan_trabajo text NOT NULL,
  descripcion_plan_trabajo text,
  tipo_frecuencia text,
  valor_frecuencia numeric(12,2),
  tiempo_ejecucion_min numeric(12,2),
  numero_personas numeric(8,2),
  tiempo_parada_min numeric(12,2),
  requiere_parada boolean GENERATED ALWAYS AS (COALESCE(tiempo_parada_min,0) > 0) STORED,
  especialidad varchar(20),
  orden_tipo varchar(20),
  estado text,
  habilitado boolean NOT NULL DEFAULT true,
  fila_origen integer,
  actualizado_en timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT plan_personas_check CHECK (numero_personas IS NULL OR numero_personas > 0),
  CONSTRAINT plan_tiempo_ejecucion_check CHECK (tiempo_ejecucion_min IS NULL OR tiempo_ejecucion_min >= 0),
  CONSTRAINT plan_tiempo_parada_check CHECK (tiempo_parada_min IS NULL OR tiempo_parada_min >= 0),
  CONSTRAINT plan_trabajo_unico UNIQUE (grupo,plan_trabajo)
);

CREATE TABLE IF NOT EXISTS programacion.planeacion (
  id bigserial PRIMARY KEY,
  id_cronograma_planeacion text NOT NULL UNIQUE,
  activo_id bigint NOT NULL REFERENCES programacion.activo(id) ON DELETE RESTRICT,
  plan_trabajo_id bigint REFERENCES programacion.plan_trabajo(id) ON DELETE SET NULL,
  plan_clave_software text NOT NULL,
  descripcion text,
  prioridad text,
  usuario text,
  fecha_inicio timestamp,
  fecha_fin timestamp,
  autogenerar_orden boolean,
  programacion_fija boolean,
  estado text,
  habilitado boolean NOT NULL DEFAULT true,
  fila_origen integer,
  actualizado_en timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS programacion.orden_mantenimiento (
  id bigserial PRIMARY KEY,
  source_key char(64) NOT NULL UNIQUE,
  periodo date NOT NULL,
  numero_ot text,
  activo_id bigint NOT NULL REFERENCES programacion.activo(id) ON DELETE RESTRICT,
  planeacion_id bigint REFERENCES programacion.planeacion(id) ON DELETE SET NULL,
  plan_trabajo_id bigint REFERENCES programacion.plan_trabajo(id) ON DELETE SET NULL,
  plan_clave_software text NOT NULL,
  titulo text,
  especialidad varchar(20),
  orden_tipo varchar(20),
  responsable text,
  cronograma_planeacion text,
  tiempo_planeado_min numeric(12,2),
  estado text,
  fila_origen integer,
  actualizado_en timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT orden_tiempo_check CHECK (tiempo_planeado_min IS NULL OR tiempo_planeado_min >= 0)
);

CREATE TABLE IF NOT EXISTS programacion.tecnico (
  id bigserial PRIMARY KEY,
  identificacion text,
  nombre text NOT NULL,
  nombre_normalizado text NOT NULL UNIQUE,
  especialidad varchar(20),
  activo boolean NOT NULL DEFAULT true,
  fila_origen integer,
  actualizado_en timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS programacion.programacion_tecnico (
  id bigserial PRIMARY KEY,
  tecnico_id bigint NOT NULL REFERENCES programacion.tecnico(id) ON DELETE CASCADE,
  fecha date NOT NULL,
  turno_codigo text NOT NULL,
  tipo_dia varchar(20) NOT NULL DEFAULT 'TRABAJO',
  horas_disponibles numeric(6,2) NOT NULL DEFAULT 0,
  fila_origen integer,
  actualizado_en timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT programacion_tecnico_horas_check CHECK (horas_disponibles >= 0),
  CONSTRAINT programacion_tecnico_unico UNIQUE (tecnico_id,fecha)
);

CREATE INDEX IF NOT EXISTS idx_planeacion_activo ON programacion.planeacion(activo_id);
CREATE INDEX IF NOT EXISTS idx_planeacion_plan ON programacion.planeacion(plan_trabajo_id);
CREATE INDEX IF NOT EXISTS idx_orden_periodo ON programacion.orden_mantenimiento(periodo);
CREATE INDEX IF NOT EXISTS idx_orden_numero_ot ON programacion.orden_mantenimiento(numero_ot);
CREATE INDEX IF NOT EXISTS idx_orden_activo ON programacion.orden_mantenimiento(activo_id);
CREATE INDEX IF NOT EXISTS idx_orden_plan ON programacion.orden_mantenimiento(plan_trabajo_id);
CREATE INDEX IF NOT EXISTS idx_programacion_tecnico_fecha ON programacion.programacion_tecnico(fecha);

COMMENT ON SCHEMA programacion IS 'Modelo V2 mínimo basado directamente en los archivos exportados por el software de mantenimiento.';
COMMENT ON TABLE programacion.activo IS 'Equipos de planta exportados por el software.';
COMMENT ON TABLE programacion.plan_trabajo IS 'Planes de trabajo del software. TiempoParada > 0 significa que requiere parada.';
COMMENT ON TABLE programacion.planeacion IS 'Relación del software entre un activo y su plan de trabajo.';
COMMENT ON TABLE programacion.orden_mantenimiento IS 'PMP/órdenes mensuales. La fecha diaria del software no gobierna la programación interna.';
COMMENT ON TABLE programacion.tecnico IS 'Técnicos incluidos en la programación mensual.';
COMMENT ON TABLE programacion.programacion_tecnico IS 'Turno diario y H-H disponibles de cada técnico.';
