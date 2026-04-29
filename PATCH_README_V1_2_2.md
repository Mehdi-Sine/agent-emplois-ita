Patch correctif V1.2.2 — ACTA + inov3PT

Contenu :
- agent/app/connectors/acta.py
- agent/app/connectors/inov3pt.py

Objectif :
- ACTA : fiabiliser la discovery et surtout la récupération du lieu depuis les cartes Welcome to the Jungle, au lieu de dériver des durées type "(9 mois)".
- inov3PT : marquer correctement les offres comme pourvues/terminées, et supprimer les entrées parasites autour de la section "Stages".

Tests locaux conseillés :

cd C:\dev\agent-emplois-ita\agent

@'
from app.connectors.acta import ActaConnector
from app.connectors.inov3pt import Inov3ptConnector
from app.http import build_http_client
from app.models import SourceConfig

client = build_http_client("ITA Jobs Bot/1.0 (+https://example.org)", 30)

for slug, name, jobs_url, cls in [
    ("acta", "ACTA", "https://www.welcometothejungle.com/fr/companies/acta/jobs", ActaConnector),
    ("inov3pt", "inov3PT", "https://www.inov3pt.fr/recrutements", Inov3ptConnector),
]:
    print("=" * 120)
    print(slug.upper(), jobs_url)
    source = SourceConfig(slug=slug, name=name, site_url=jobs_url.split('/recrutements')[0] if slug == 'inov3pt' else 'https://www.acta.asso.fr', jobs_url=jobs_url, enabled=True, mode='http', timeout_seconds=30)
    connector = cls(source)
    urls = connector.discover_offer_urls(client)
    print("discover_count:", len(urls))
    for url in urls[:10]:
        raw = connector.parse_offer(client, url)
        print(raw)
'@ | .\.venv\Scripts\python.exe -

Backfill ciblé :

$env:SUPABASE_URL="https://VOTRE-PROJET.supabase.co"
$env:SUPABASE_SERVICE_KEY="VOTRE_SERVICE_ROLE_KEY"
$env:JOBS_ARCHIVE_MISSED_THRESHOLD="2"
$env:USER_AGENT="ITA Jobs Bot/1.0 (+local test)"

python -m app.main_backfill_sources --source acta
python -m app.main_backfill_sources --source inov3pt

SQL de contrôle :

select s.slug, o.title, o.location_text, o.city, o.contract_type, o.offer_type, o.is_active, o.archived_at, o.source_url
from offers o
join sources s on s.id = o.source_id
where s.slug in ('acta','inov3pt')
order by s.slug, o.updated_at desc;
