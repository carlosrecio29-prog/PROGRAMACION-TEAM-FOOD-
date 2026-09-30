create table if not exists programacion.programming_test_restore_point (
  id bigint generated always as identity primary key,
  nombre text not null unique,
  creado_en timestamptz not null default now(),
  programaciones integer not null,
  items integer not null,
  backlog integer not null,
  cierres integer not null,
  cierre_items integer not null,
  cierres_mensuales integer not null,
  nota text null
);

revoke all on table programacion.programming_test_restore_point from public;

insert into programacion.programming_test_restore_point(
  nombre, programaciones, items, backlog, cierres, cierre_items, cierres_mensuales, nota
)
select
  'ANTES_PRIMERA_PROGRAMACION_REAL_20260930',
  (select count(*) from programacion.programacion_semanal_v2),
  (select count(*) from programacion.programacion_item_v2),
  (select count(*) from programacion.backlog_v2),
  (select count(*) from programacion.cierre_semanal_v2),
  (select count(*) from programacion.cierre_item_v2),
  (select count(*) from programacion.cierre_mensual_v2),
  'Punto de retorno solicitado antes de iniciar la primera prueba real de programación semanal.'
on conflict (nombre) do nothing;
