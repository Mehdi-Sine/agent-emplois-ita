-- V1.2 - ajout / mise à jour des 6 nouvelles sources
-- Hypothèse de schéma source conforme aux usages du projet :
-- slug, name, site_url, jobs_url, enabled, mode, timeout_seconds

insert into sources (slug, name, site_url, jobs_url, enabled, mode, timeout_seconds)
values
  ('acta', 'ACTA', 'https://www.acta.asso.fr', 'https://www.welcometothejungle.com/fr/companies/acta/jobs', true, 'http', 30),
  ('armeflhor', 'ARMEFLHOR', 'https://www.armeflhor.fr', 'https://www.armeflhor.fr/category/recrutement/', true, 'http', 30),
  ('astredhor', 'ASTREDHOR', 'https://institut-du-vegetal.fr', 'https://institut-du-vegetal.fr/nous-rejoindre/', true, 'http', 30),
  ('ceva', 'CEVA', 'https://www.ceva-algues.com', 'https://www.ceva-algues.com/le-ceva/recrutement/', true, 'http', 30),
  ('inov3pt', 'inov3PT', 'https://www.inov3pt.fr', 'https://www.inov3pt.fr/recrutements', true, 'http', 30),
  ('cnpf', 'CNPF', 'https://www.cnpf.fr', 'https://www.cnpf.fr/le-cnpf-recrute', true, 'http', 30)
on conflict (slug) do update
set
  name = excluded.name,
  site_url = excluded.site_url,
  jobs_url = excluded.jobs_url,
  enabled = excluded.enabled,
  mode = excluded.mode,
  timeout_seconds = excluded.timeout_seconds;
