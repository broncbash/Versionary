"""Dashboard delivery, browser safety and read-only contract."""
import unittest
from fastapi.testclient import TestClient
from main import app


class DashboardUITests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_dashboard_available(self):
        response = self.client.get("/admin/dashboard")
        self.assertEqual(response.status_code, 200)
        self.assertIn("PATCH COMMAND", response.text)
        self.assertIn("Infrastructure monitoring · Observer mode", response.text)

    def test_dashboard_uses_authenticated_read_only_inventory(self):
        page = self.client.get("/admin/dashboard").text
        self.assertIn("fetch('/api/v1/admin/agents'", page)
        self.assertIn("cache:'no-store'", page)
        self.assertIn("credentials:'omit'", page)
        self.assertIn("Bearer '+credential", page)
        self.assertNotIn("localStorage", page)
        self.assertNotIn("sessionStorage", page)

    def test_dashboard_escapes_untrusted_agent_fields(self):
        page = self.client.get("/admin/dashboard").text
        self.assertIn("element.textContent=text", page)
        self.assertIn("card.append(node('h3',a.hostname)", page)
        self.assertNotIn("innerHTML", page)

    def test_dashboard_security_headers(self):
        response = self.client.get("/admin/dashboard")
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertIn("frame-ancestors 'none'", response.headers["content-security-policy"])
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")

    def test_dashboard_no_mutation_controls(self):
        page = self.client.get("/admin/dashboard").text
        self.assertNotIn("method:'POST'", page)
        self.assertNotIn("method:'PATCH'", page)
        self.assertIn("No scans, approvals, service changes", page)


if __name__ == "__main__":
    unittest.main()
