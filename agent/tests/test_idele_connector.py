import unittest

from app.connectors.idele import IdeleConnector
from app.models import SourceConfig


class IdeleConnectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.connector = IdeleConnector(
            SourceConfig(
                slug="idele",
                name="IDELE",
                site_url="https://idele.fr",
                jobs_url="https://idele.fr/recrutement",
            )
        )

    def test_menu_text_does_not_mark_offer_filled(self) -> None:
        lines = ["Retour aux offres", "Offres terminées", "Partager sur :"]
        self.assertFalse(self.connector._is_filled(lines))

    def test_unavailable_message_marks_offer_filled(self) -> None:
        lines = ["Cette offre n'est plus disponible", "Retour aux offres"]
        self.assertTrue(self.connector._is_filled(lines))


if __name__ == "__main__":
    unittest.main()
