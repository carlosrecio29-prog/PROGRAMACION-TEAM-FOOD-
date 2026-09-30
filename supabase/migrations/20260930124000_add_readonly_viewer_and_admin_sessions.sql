create table if not exists programacion.app_admin_auth (
  id smallint primary key check (id = 1),
  password_salt text not null,
  password_hash text not null,
  iterations integer not null check (iterations >= 100000),
  updated_at timestamptz not null default now()
);

create table if not exists programacion.app_admin_session (
  token_hash text primary key,
  created_at timestamptz not null default now(),
  expires_at timestamptz not null,
  revoked_at timestamptz null
);

create index if not exists app_admin_session_expires_idx
  on programacion.app_admin_session (expires_at);

revoke all on table programacion.app_admin_auth from public;
revoke all on table programacion.app_admin_session from public;
