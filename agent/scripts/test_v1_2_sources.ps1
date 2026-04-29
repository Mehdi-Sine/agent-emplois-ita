param()

Set-Location (Join-Path $PSScriptRoot "..")

@'
from app.http import build_http_client
from app.models import SourceConfig

from app.connectors.acta import ActaConnector
from app.connectors.armeflhor import ArmeflhorConnector
from app.connectors.astredhor import AstredhorConnector
from app.connectors.ceva import CevaConnector
from app.connectors.inov3pt import Inov3ptConnector
from app.connectors.cnpf import CnpfConnector

sources = [
    ("acta", ActaConnector, "ACTA", "https://www.acta.asso.fr", "https://www.welcometothejungle.com/fr/companies/acta/jobs"),
    ("armeflhor", ArmeflhorConnector, "ARMEFLHOR", "https://www.armeflhor.fr", "https://www.armeflhor.fr/category/recrutement/"),
    ("astredhor", AstredhorConnector, "ASTREDHOR", "https://institut-du-vegetal.fr", "https://institut-du-vegetal.fr/nous-rejoindre/"),
    ("ceva", CevaConnector, "CEVA", "https://www.ceva-algues.com", "https://www.ceva-algues.com/le-ceva/recrutement/"),
    ("inov3pt", Inov3ptConnector, "inov3PT", "https://www.inov3pt.fr", "https://www.inov3pt.fr/recrutements"),
    ("cnpf", CnpfConnector, "CNPF", "https://www.cnpf.fr", "https://www.cnpf.fr/le-cnpf-recrute"),
]

client = build_http_client("ITA Jobs Bot/1.2 (+https://example.org)", 30)

for slug, klass, name, site_url, jobs_url in sources:
    print("=" * 120)
    print(slug.upper(), jobs_url)
    source = SourceConfig(
        slug=slug,
        name=name,
        site_url=site_url,
        jobs_url=jobs_url,
        enabled=True,
        mode="http",
        timeout_seconds=30,
    )
    connector = klass(source)
    urls = connector.discover_offer_urls(client)
    print("discover_count:", len(urls))
    for url in urls[:5]:
        print("-", url)

    for url in urls[:3]:
        raw = connector.parse_offer(client, url)
        print("RAW:", raw)
        print("-" * 80)
'@ | .\.venv\Scripts\python.exe -
