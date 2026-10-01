alter table programacion.programacion_semanal_v2
  add column if not exists hh_objetivo_anterior numeric,
  add column if not exists capacidad_modificada_en timestamptz;
