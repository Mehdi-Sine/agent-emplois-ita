create extension if not exists pgcrypto;

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table if not exists public.sources (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  name text not null,
  site_url text not null,
  jobs_url text not null,
  is_enabled boolean not null default true,
  connector_type text not null default 'http',
  config_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.pipeline_runs (
  id uuid primary key default gen_random_uuid(),
  trigger_type text not null default 'cron',
  started_at timestamptz not null default now(),
  ended_at timestamptz,
  status text not null default 'SUCCESS',
  total_sources integer not null default 0,
  sources_success integer not null default 0,
  sources_failed integer not null default 0,
  new_offers integer not null default 0,
  updated_offers integer not null default 0,
  archived_offers integer not null default 0,
  summary_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.source_runs (
  id uuid primary key default gen_random_uuid(),
  pipeline_run_id uuid not null references public.pipeline_runs(id) on delete cascade,
  source_id uuid not null references public.sources(id) on delete cascade,
  started_at timestamptz not null default now(),
  ended_at timestamptz,
  status text not null default 'FAILED',
  offers_found integer not null default 0,
  offers_new integer not null default 0,
  offers_updated integer not null default 0,
  offers_archived integer not null default 0,
  http_errors integer not null default 0,
  parse_errors integer not null default 0,
  error_message text,
  raw_output_path text,
  normalized_output_path text,
  metrics_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.offers (
  id uuid primary key default gen_random_uuid(),
  source_id uuid not null references public.sources(id) on delete cascade,
  last_source_run_id uuid references public.source_runs(id) on delete set null,
  source_offer_key text not null,
  source_url text not null,
  application_url text,
  title text not null,
  organization text not null,
  location_text text,
  city text,
  region text,
  country text default 'France',
  contract_type text,
  offer_type text,
  remote_mode text,
  posted_at timestamptz,
  description_text text,
  content_hash text not null,
  is_active boolean not null default true,
  first_seen_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now(),
  archived_at timestamptz,
  consecutive_missed_runs integer not null default 0,
  raw_payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint offers_source_key_unique unique (source_id, source_offer_key)
);

create table if not exists public.offer_snapshots (
  id uuid primary key default gen_random_uuid(),
  offer_id uuid not null references public.offers(id) on delete cascade,
  source_run_id uuid not null references public.source_runs(id) on delete cascade,
  seen_at timestamptz not null default now(),
  content_hash text not null,
  title text not null,
  location_text text,
  contract_type text,
  offer_type text,
  posted_at timestamptz,
  raw_payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_source_runs_pipeline on public.source_runs (pipeline_run_id);
create index if not exists idx_source_runs_source on public.source_runs (source_id, started_at desc);
create index if not exists idx_offers_active on public.offers (is_active, last_seen_at desc);
create index if not exists idx_offers_source on public.offers (source_id, is_active);
create index if not exists idx_offers_offer_type on public.offers (offer_type);
create index if not exists idx_offer_snapshots_offer on public.offer_snapshots (offer_id, seen_at desc);

drop trigger if exists trg_sources_updated_at on public.sources;
create trigger trg_sources_updated_at
before update on public.sources
for each row execute function public.set_updated_at();

drop trigger if exists trg_pipeline_runs_updated_at on public.pipeline_runs;
create trigger trg_pipeline_runs_updated_at
before update on public.pipeline_runs
for each row execute function public.set_updated_at();

drop trigger if exists trg_source_runs_updated_at on public.source_runs;
create trigger trg_source_runs_updated_at
before update on public.source_runs
for each row execute function public.set_updated_at();

drop trigger if exists trg_offers_updated_at on public.offers;
create trigger trg_offers_updated_at
before update on public.offers
for each row execute function public.set_updated_at();

create or replace view public.v_active_offers as
select
  o.id,
  s.slug as source_slug,
  s.name as source_name,
  o.title,
  o.organization,
  o.location_text,
  o.contract_type,
  o.offer_type,
  o.remote_mode,
  o.posted_at,
  o.first_seen_at,
  o.last_seen_at,
  o.source_url,
  o.application_url
from public.offers o
join public.sources s on s.id = o.source_id
where o.is_active = true
order by o.last_seen_at desc;

create or replace view public.v_archived_offers as
select
  o.id,
  s.slug as source_slug,
  s.name as source_name,
  o.title,
  o.organization,
  o.location_text,
  o.contract_type,
  o.offer_type,
  o.posted_at,
  o.first_seen_at,
  o.last_seen_at,
  o.archived_at,
  o.source_url
from public.offers o
join public.sources s on s.id = o.source_id
where o.is_active = false
order by o.archived_at desc nulls last;

create or replace view public.v_source_latest_status as
with ranked as (
  select
    sr.*,
    row_number() over (partition by sr.source_id order by sr.started_at desc) as rn
  from public.source_runs sr
)
select
  s.id as source_id,
  s.slug as source_slug,
  s.name as source_name,
  s.jobs_url,
  r.id as source_run_id,
  r.started_at,
  r.ended_at,
  r.status,
  r.offers_found,
  r.offers_new,
  r.offers_updated,
  r.offers_archived,
  r.http_errors,
  r.parse_errors,
  r.error_message,
  r.metrics_json
from public.sources s
left join ranked r on r.source_id = s.id and r.rn = 1
order by s.name;
