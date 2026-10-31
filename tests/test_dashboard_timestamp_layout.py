"""Dashboard timestamp formatting and responsive layout contract."""
import unittest

from fastapi.testclient import TestClient
from main import app


class DashboardTimestampLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with TestClient(app) as client:
            response = client.get("/admin/dashboard")
        assert response.status_code == 200
        cls.page = response.text

    def test_localized_timestamp_formatter(self):
        self.assertIn("function formatTimestamp(value)", self.page)
        self.assertIn("new Intl.DateTimeFormat(undefined", self.page)
        self.assertIn("timeZoneName:'short'", self.page)
        self.assertIn("Invalid timestamp", self.page)

    def test_timestamp_fields_use_formatter(self):
        self.assertIn("formatTimestamp(a.last_seen)", self.page)
        self.assertIn("formatTimestamp(a.scan_at)", self.page)
        self.assertIn("detail.title=", self.page)

    def test_responsive_card_layout(self):
        self.assertIn("minmax(min(100%,350px),1fr)", self.page)
        self.assertIn("@media(max-width:420px)", self.page)

    def test_observer_only_security_contract(self):
        self.assertNotIn("innerHTML", self.page)
        self.assertNotIn("localStorage", self.page)
        self.assertNotIn("sessionStorage", self.page)
        self.assertNotIn("method:'POST'", self.page)
        self.assertNotIn("method:'PATCH'", self.page)


if __name__ == "__main__":
    unittest.main()
