create table if not exists programacion.seguimiento_semanal_v2 (
  id bigserial primary key,
  programacion_id bigint not null references programacion.programacion_semanal_v2(id) on delete cascade,
  archivo_nombre text not null,
  registrado_por text,
  registrado_en timestamptz not null default now(),
  total_items integer not null default 0,
  finalizados integer not null default 0,
  pendientes integer not null default 0,
  sin_coincidencia integer not null default 0,
  hh_programadas numeric not null default 0,
  hh_finalizadas numeric not null default 0,
  hh_pendientes numeric not null default 0,
  avance_ot_pct numeric not null default 0,
  avance_hh_pct numeric not null default 0
);

create index if not exists ix_seguimiento_semanal_v2_programacion
  on programacion.seguimiento_semanal_v2(programacion_id, registrado_en desc);

create table if not exists programacion.seguimiento_semanal_item_v2 (
  id bigserial primary key,
  seguimiento_id bigint not null references programacion.seguimiento_semanal_v2(id) on delete cascade,
  programacion_item_id bigint not null references programacion.programacion_item_v2(id) on delete cascade,
  orden_mantenimiento_id bigint not null references programacion.orden_mantenimiento(id) on delete cascade,
  numero_ot text,
  area_codigo text,
  area_nombre text,
  hh_programadas numeric not null default 0,
  estado_calendario text,
  finalizado boolean,
  coincidencia text,
  registrado_en timestamptz not null default now(),
  constraint seguimiento_semanal_item_v2_unique unique(seguimiento_id, programacion_item_id)
);

create index if not exists ix_seguimiento_item_v2_seguimiento
  on programacion.seguimiento_semanal_item_v2(seguimiento_id);
create index if not exists ix_seguimiento_item_v2_area
  on programacion.seguimiento_semanal_item_v2(seguimiento_id, area_codigo);

alter table programacion.seguimiento_semanal_v2 enable row level security;
alter table programacion.seguimiento_semanal_item_v2 enable row level security;
revoke all on table programacion.seguimiento_semanal_v2 from public;
revoke all on table programacion.seguimiento_semanal_item_v2 from public;
