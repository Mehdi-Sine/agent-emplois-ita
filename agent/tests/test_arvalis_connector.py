from types import SimpleNamespace

import pytest

from app.connectors.arvalis import ArvalisConnector
from app.models import SourceConfig


def connector() -> ArvalisConnector:
    return ArvalisConnector(
        SourceConfig(
            slug="arvalis",
            name="ARVALIS",
            site_url="https://www.arvalis.fr",
            jobs_url=ArvalisConnector.LISTING_URL,
            enabled=True,
            mode="http",
        )
    )


def test_extracts_offer_links_from_public_listing() -> None:
    html = '''
      <a href="/l-institut/nous-rejoindre/offres-d-emploi-de-stages/ingenieur-agronome">
        Ingénieur agronome
      </a>
      <a href="/l-institut/nous-rejoindre/offres-d-emploi-de-stages/candidature-spontanee">Candidature</a>
    '''

    assert connector()._extract_offer_links(html, ArvalisConnector.LISTING_URL) == [
        "https://www.arvalis.fr/l-institut/nous-rejoindre/offres-d-emploi-de-stages/ingenieur-agronome"
    ]


def test_reads_current_algolia_credentials_instead_of_static_key() -> None:
    html = '''window.search = {
      "applicationId": "NEWAPP123",
      "searchApiKey": "rotated-search-only-key",
      "indexName": "current_job_offers"
    };'''

    assert connector()._extract_algolia_credentials(html) == (
        "NEWAPP123",
        "rotated-search-only-key",
        "current_job_offers",
    )


def test_missing_links_and_search_config_fails_safely() -> None:
    response = SimpleNamespace(
        text="<html><body>Aucune configuration de recherche</body></html>",
        url=ArvalisConnector.LISTING_URL,
        raise_for_status=lambda: None,
    )
    client = SimpleNamespace(get=lambda _url: response)

    with pytest.raises(RuntimeError, match="archivage erroné"):
        connector().discover_offer_urls(client)
