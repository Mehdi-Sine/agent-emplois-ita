-- V1.2 - ajout / mise à jour de 6 sources selon votre schéma public.sources
-- Colonnes disponibles : slug, name, site_url, jobs_url, is_enabled, connector_type, config_json, created_at, updated_at

insert into public.sources (
  slug,
  name,
  site_url,
  jobs_url,
  is_enabled,
  connector_type,
  config_json
)
values
  ('acta', 'ACTA', 'https://www.acta.asso.fr', 'https://www.welcometothejungle.com/fr/companies/acta/jobs', true, 'http', '{}'::jsonb),
  ('armeflhor', 'ARMEFLHOR', 'https://www.armeflhor.fr', 'https://www.armeflhor.fr/category/recrutement/', true, 'http', '{}'::jsonb),
  ('astredhor', 'ASTREDHOR', 'https://institut-du-vegetal.fr', 'https://institut-du-vegetal.fr/nous-rejoindre/', true, 'http', '{}'::jsonb),
  ('ceva', 'CEVA', 'https://www.ceva-algues.com', 'https://www.ceva-algues.com/le-ceva/recrutement/', true, 'http', '{}'::jsonb),
  ('inov3pt', 'inov3PT', 'https://www.inov3pt.fr', 'https://www.inov3pt.fr/recrutements', true, 'http', '{}'::jsonb),
  ('cnpf', 'CNPF', 'https://www.cnpf.fr', 'https://www.cnpf.fr/le-cnpf-recrute', true, 'http', '{}'::jsonb)
on conflict (slug) do update
set
  name = excluded.name,
  site_url = excluded.site_url,
  jobs_url = excluded.jobs_url,
  is_enabled = excluded.is_enabled,
  connector_type = excluded.connector_type,
  config_json = coalesce(public.sources.config_json, '{}'::jsonb) || excluded.config_json,
  updated_at = now();

-- Contrôle rapide après insertion
select
  slug,
  name,
  site_url,
  jobs_url,
  is_enabled,
  connector_type,
  updated_at
from public.sources
where slug in ('acta', 'armeflhor', 'astredhor', 'ceva', 'inov3pt', 'cnpf')
order by slug;
