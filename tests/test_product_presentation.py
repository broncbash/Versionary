"""Product naming and compatibility guardrails for browser-facing pages."""
import unittest

from fastapi.testclient import TestClient
from main import app


class ProductPresentationTests(unittest.TestCase):
    def test_administrative_pages_use_product_name(self):
        with TestClient(app) as client:
            for path in ("/admin/dashboard", "/admin/settings"):
                with self.subTest(path=path):
                    response = client.get(path)
                    self.assertEqual(response.status_code, 200)
                    self.assertIn("Patch Command", response.text)
                    self.assertNotIn("ARBY", response.text.upper())
                    self.assertNotIn("CYBERPUNK", response.text.upper())

    def test_legacy_appearance_value_is_accepted_without_legacy_label(self):
        with TestClient(app) as client:
            response = client.get("/admin/settings")
        self.assertIn('value="cyberpunk"', response.text)
        self.assertIn('Classic (legacy compatibility)', response.text)
        self.assertNotIn('>Cyberpunk<', response.text)

    def test_dashboard_is_still_observer_only(self):
        with TestClient(app) as client:
            response = client.get("/admin/dashboard")
        self.assertIn("Observer mode", response.text)
        self.assertIn("Read-only dashboard", response.text)


if __name__ == "__main__":
    unittest.main()
