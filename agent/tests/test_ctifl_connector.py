import unittest

from app.connectors.ctifl import CtiflConnector
from app.models import SourceConfig


class CtiflConnectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.connector = CtiflConnector(
            SourceConfig(
                slug="ctifl",
                name="CTIFL",
                site_url="https://www.ctifl.fr",
                jobs_url="https://www.ctifl.fr/recrutement",
            )
        )

    def test_offres_terminees_menu_does_not_mark_offer_filled(self) -> None:
        lines = ["Retour aux offres", "Offres terminées", "Partager sur :"]
        self.assertFalse(self.connector._is_filled(lines))

    def test_unavailable_message_marks_offer_filled(self) -> None:
        lines = ["Cette offre n'est plus disponible", "Retour aux offres"]
        self.assertTrue(self.connector._is_filled(lines))


if __name__ == "__main__":
    unittest.main()
