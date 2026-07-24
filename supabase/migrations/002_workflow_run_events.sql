create table if not exists public.workflow_run_events (
  id uuid primary key default gen_random_uuid(),
  event_type text not null,
  status text not null,
  occurred_at timestamptz not null default now(),
  github_run_id text,
  github_run_attempt text,
  github_workflow text,
  github_event_name text,
  github_ref text,
  github_sha text,
  github_actor text,
  pipeline_run_id uuid references public.pipeline_runs(id) on delete set null,
  details_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_workflow_run_events_occurred on public.workflow_run_events (occurred_at desc);
create index if not exists idx_workflow_run_events_github_run on public.workflow_run_events (github_run_id, github_run_attempt);
create index if not exists idx_workflow_run_events_pipeline on public.workflow_run_events (pipeline_run_id);
