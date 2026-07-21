import unittest

from app.connectors.ceva import CevaConnector
from app.models import SourceConfig


class CevaConnectorTests(unittest.TestCase):
    def setUp(self) -> None:
        source = SourceConfig(
            slug="ceva",
            name="CEVA",
            site_url="https://www.ceva-algues.com",
            jobs_url="https://www.ceva-algues.com/le-ceva/recrutement/",
        )
        self.connector = CevaConnector(source)

    def test_infers_ile_de_france_location_from_description(self) -> None:
        location_text, city, region = self.connector._infer_location(
            "CDD TECHNICIEN(NE) SPECIALISE(E) EN CHIMIE ANALYTIQUE (15 MOIS)",
            "Le poste est basé à Maisons-Alfort (94)",
        )

        self.assertEqual(location_text, "Maisons-Alfort (94)")
        self.assertEqual(city, "Maisons-Alfort")
        self.assertEqual(region, "Île-de-France")

    def test_marks_offer_filled_when_closed_marker_present(self) -> None:
        self.assertTrue(self.connector._is_filled("OFFRE D'EMPLOI", "Poste pourvu"))
        self.assertFalse(self.connector._is_filled("OFFRE D'EMPLOI", "Mission en cours"))

    def test_extracts_stage_offer_title(self) -> None:
        lines = [
            "Recrutement",
            "OFFRE DE STAGE :",
            "Offre de stage_Stratégie Marketing & Développement. International – F/H.",
            "Partagez cette page :",
        ]

        self.assertEqual(
            self.connector._extract_title(lines),
            "Offre de stage_Stratégie Marketing & Développement. International – F/H.",
        )


if __name__ == "__main__":
    unittest.main()
