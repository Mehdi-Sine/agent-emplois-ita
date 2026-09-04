import unittest

from app.connectors.acta import ActaConnector
from app.connectors.common import html_tree
from app.models import SourceConfig


class ActaConnectorTests(unittest.TestCase):
    def setUp(self) -> None:
        source = SourceConfig(
            slug="acta",
            name="ACTA",
            site_url="https://www.acta.asso.fr",
            jobs_url="https://www.welcometothejungle.com/fr/companies/acta/jobs",
        )
        self.connector = ActaConnector(source)

    def test_canonicalizes_wttj_companies_v1_to_stable_french_job_url(self) -> None:
        url = self.connector._canonicalize_offer_url(
            "https://www.welcometothejungle.com/fr/companies-v1/acta/jobs/assistant_paris_ABC?utm=ignored"
        )

        self.assertEqual(
            url,
            "https://www.welcometothejungle.com/fr/companies/acta/jobs/assistant_paris_ABC",
        )

    def test_canonicalizes_english_wttj_job_url_to_stable_french_job_url(self) -> None:
        url = self.connector._canonicalize_offer_url(
            "https://www.welcometothejungle.com/en/companies/acta/jobs/assistant_paris_ABC"
        )

        self.assertEqual(
            url,
            "https://www.welcometothejungle.com/fr/companies/acta/jobs/assistant_paris_ABC",
        )

    def test_extracts_offer_links_from_raw_wttj_paths_when_cards_are_not_rendered(self) -> None:
        html = """
        <html><body>
          <script>
            window.__DATA__ = {"href":"/fr/companies-v1/acta/jobs/assistant_paris_ABC"};
            window.__OTHER__ = {"href":"/fr/companies-v1/acta/jobs/candidatures-spontanees"};
          </script>
        </body></html>
        """
        seen: set[str] = set()
        urls: list[str] = []
        for match in self.connector.RAW_JOB_PATH_RE.finditer(html):
            url = self.connector._canonicalize_offer_url(
                f"https://www.welcometothejungle.com{match.group('path')}"
            )
            if url and "spontan" not in url.lower() and url not in seen:
                seen.add(url)
                urls.append(url)

        self.assertEqual(
            urls,
            ["https://www.welcometothejungle.com/fr/companies/acta/jobs/assistant_paris_ABC"],
        )

    def test_configured_seed_offer_urls_are_canonicalized(self) -> None:
        source = SourceConfig(
            slug="acta",
            name="ACTA",
            site_url="https://www.acta.asso.fr",
            jobs_url="https://www.welcometothejungle.com/fr/companies/acta/jobs",
            seed_offer_urls=[
                "https://www.welcometothejungle.com/fr/companies-v1/acta/jobs/assistant_paris_ABC?utm=ignored",
                "https://www.welcometothejungle.com/fr/companies-v1/acta/jobs/candidatures-spontanees",
            ],
        )
        connector = ActaConnector(source)

        self.assertEqual(
            connector._configured_seed_offer_urls(),
            ["https://www.welcometothejungle.com/fr/companies/acta/jobs/assistant_paris_ABC"],
        )

    def test_configured_seed_is_an_explicit_open_signal(self) -> None:
        source = SourceConfig(
            slug="acta",
            name="ACTA",
            site_url="https://www.acta.asso.fr",
            jobs_url="https://www.welcometothejungle.com/fr/companies/acta/jobs",
            seed_offer_urls=[
                "https://www.welcometothejungle.com/fr/companies/acta/jobs/assistant_paris_ABC"
            ],
        )
        connector = ActaConnector(source)

        class Response:
            status_code = 200
            text = "<html><body></body></html>"
            url = source.jobs_url

            @staticmethod
            def raise_for_status() -> None:
                return None

        urls = connector.discover_offer_urls(type("Client", (), {"get": lambda self, url: Response()})())

        self.assertEqual(urls, source.seed_offer_urls)
        self.assertTrue(connector._listing_by_url[urls[0]]["listed_as_open"])

    def test_listing_presence_keeps_offer_active_despite_generic_closed_copy(self) -> None:
        self.assertFalse(
            self.connector._is_filled("Cette offre n'est plus disponible", listed_as_open=True)
        )

    def test_seeded_offer_stays_open_despite_generic_closed_title(self) -> None:
        self.assertFalse(
            self.connector._is_filled("Cette offre n'est plus disponible", listed_as_open=True)
        )

    def test_explicit_closed_page_title_marks_seed_only_offer_as_filled(self) -> None:
        self.assertTrue(
            self.connector._is_filled("Cette offre n'est plus disponible", listed_as_open=False)
        )

    def test_ignores_generic_closed_heading_when_extracting_offer_title(self) -> None:
        tree = html_tree(
            """
            <html><body>
              <h1>Cette offre n'est plus disponible</h1>
              <h2>Assistant administratif et financier</h2>
            </body></html>
            """
        )

        self.assertEqual(
            self.connector._extract_offer_title(tree),
            "Assistant administratif et financier",
        )


if __name__ == "__main__":
    unittest.main()
