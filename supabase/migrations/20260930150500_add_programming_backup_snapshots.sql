create table if not exists programacion.programming_backup_snapshot (
  id bigint generated always as identity primary key,
  nombre text not null unique,
  descripcion text null,
  creado_en timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb,
  programaciones jsonb not null default '[]'::jsonb,
  items jsonb not null default '[]'::jsonb,
  backlog jsonb not null default '[]'::jsonb,
  cierres jsonb not null default '[]'::jsonb,
  cierre_items jsonb not null default '[]'::jsonb,
  cierres_mensuales jsonb not null default '[]'::jsonb
);

revoke all on table programacion.programming_backup_snapshot from public;
alter table programacion.programming_backup_snapshot enable row level security;
