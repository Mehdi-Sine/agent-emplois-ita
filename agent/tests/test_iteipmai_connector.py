import unittest

from app.connectors.iteipmai import IteipmaiConnector
from app.models import SourceConfig


class IteipmaiConnectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.connector = IteipmaiConnector(
            SourceConfig(
                slug="iteipmai",
                name="ITEIPMAI",
                site_url="https://www.iteipmai.fr",
                jobs_url="https://www.iteipmai.fr/emplois-stages/",
            )
        )

    def test_only_actualite_urls_are_kept(self) -> None:
        self.assertTrue(self.connector._is_internal_offer_url("https://www.iteipmai.fr/actualite/offre-demploi-2026-assistant-tech/"))
        self.assertFalse(self.connector._is_internal_offer_url("https://www.iteipmai.fr/2025-labo-cdd_compressed/"))

    def test_plural_status_header_does_not_mark_offer_filled(self) -> None:
        paragraphs = ["Publiée le 27 janvier 2026", "3 postes en CDD", "ANNONCES POURVUES"]
        self.assertFalse(self.connector._extract_is_filled(paragraphs, "3 assistant(e)s techniques d’expérimentation"))

    def test_annonce_pourvue_marker_marks_offer_filled(self) -> None:
        paragraphs = ["Publiée le 26 janvier 2026", "Poste en CDD", "ANNONCE POURVUE"]
        self.assertTrue(self.connector._extract_is_filled(paragraphs, "Technicien(ne) de laboratoire"))


if __name__ == "__main__":
    unittest.main()
