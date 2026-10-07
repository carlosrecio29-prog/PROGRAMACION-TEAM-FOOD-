create table if not exists programacion.seguimiento_no_programado_v2 (
  id bigserial primary key,
  programacion_id bigint not null references programacion.programacion_semanal_v2(id) on delete cascade,
  orden_mantenimiento_id bigint references programacion.orden_mantenimiento(id) on delete set null,
  numero_ot text not null,
  activo_codigo text,
  activo_descripcion text,
  area_codigo text,
  area_nombre text,
  plan_trabajo text,
  especialidad text,
  estado_calendario text,
  fecha_fin_orden timestamp without time zone,
  tiempo_planeado_min numeric,
  hh_estimada numeric not null default 0,
  origen text not null,
  detalle_origen text,
  programacion_origen_id bigint references programacion.programacion_semanal_v2(id) on delete set null,
  semana_origen_inicio date,
  semana_origen_fin date,
  primera_seguimiento_id bigint references programacion.seguimiento_semanal_v2(id) on delete set null,
  ultima_seguimiento_id bigint references programacion.seguimiento_semanal_v2(id) on delete set null,
  primera_deteccion_en timestamptz not null default now(),
  ultima_deteccion_en timestamptz not null default now(),
  veces_detectada integer not null default 1,
  constraint seguimiento_no_programado_v2_unique unique(programacion_id, numero_ot)
);

create index if not exists ix_seguimiento_no_programado_programacion
  on programacion.seguimiento_no_programado_v2(programacion_id, primera_deteccion_en desc);
create index if not exists ix_seguimiento_no_programado_orden
  on programacion.seguimiento_no_programado_v2(orden_mantenimiento_id);
create index if not exists ix_seguimiento_no_programado_ultima_carga
  on programacion.seguimiento_no_programado_v2(programacion_id, ultima_seguimiento_id);
create index if not exists ix_seguimiento_no_programado_programacion_origen
  on programacion.seguimiento_no_programado_v2(programacion_origen_id);
create index if not exists ix_seguimiento_no_programado_primera_carga
  on programacion.seguimiento_no_programado_v2(primera_seguimiento_id);
create index if not exists ix_seguimiento_no_programado_ultima_seguimiento
  on programacion.seguimiento_no_programado_v2(ultima_seguimiento_id);

alter table programacion.seguimiento_no_programado_v2 enable row level security;
revoke all on table programacion.seguimiento_no_programado_v2 from public;
