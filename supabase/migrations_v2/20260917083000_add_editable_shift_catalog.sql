create table if not exists programacion.turno_config (
  codigo text primary key,
  horas numeric(6,2) not null default 0 check (horas >= 0 and horas <= 24),
  es_ausencia boolean not null default false,
  activo boolean not null default true,
  actualizado_en timestamptz not null default now()
);

insert into programacion.turno_config(codigo, horas, es_ausencia, activo)
select
  turno_codigo,
  max(horas_disponibles)::numeric(6,2) as horas,
  bool_and(tipo_dia <> 'TRABAJO') as es_ausencia,
  true
from programacion.programacion_tecnico
where turno_codigo is not null and btrim(turno_codigo) <> ''
group by turno_codigo
on conflict (codigo) do nothing;

create or replace function programacion.apply_turno_config_to_schedule()
returns trigger
language plpgsql
as $$
begin
  update programacion.programacion_tecnico
     set horas_disponibles = case when tipo_dia = 'TRABAJO' then new.horas else 0 end,
         actualizado_en = now()
   where turno_codigo = new.codigo;
  return new;
end;
$$;

drop trigger if exists trg_apply_turno_config_to_schedule on programacion.turno_config;
create trigger trg_apply_turno_config_to_schedule
after insert or update of horas, activo on programacion.turno_config
for each row execute function programacion.apply_turno_config_to_schedule();

create or replace function programacion.use_turno_config_on_schedule()
returns trigger
language plpgsql
as $$
declare
  configured_hours numeric(6,2);
begin
  if new.tipo_dia <> 'TRABAJO' then
    new.horas_disponibles := 0;
    insert into programacion.turno_config(codigo, horas, es_ausencia, activo)
    values (new.turno_codigo, 0, true, true)
    on conflict (codigo) do nothing;
    return new;
  end if;

  select horas into configured_hours
    from programacion.turno_config
   where codigo = new.turno_codigo and activo = true;

  if found then
    new.horas_disponibles := configured_hours;
  else
    insert into programacion.turno_config(codigo, horas, es_ausencia, activo)
    values (new.turno_codigo, coalesce(new.horas_disponibles, 0), false, true)
    on conflict (codigo) do nothing;
  end if;
  return new;
end;
$$;

drop trigger if exists trg_use_turno_config_on_schedule on programacion.programacion_tecnico;
create trigger trg_use_turno_config_on_schedule
before insert or update of turno_codigo, tipo_dia on programacion.programacion_tecnico
for each row execute function programacion.use_turno_config_on_schedule();

create index if not exists idx_programacion_tecnico_turno_codigo
  on programacion.programacion_tecnico(turno_codigo);
