"""Distribution badge rendering contract."""
import unittest

from fastapi.testclient import TestClient
from main import app


class DashboardDistroBadgeTests(unittest.TestCase):
    def test_cachyos_has_distinct_badge(self):
        with TestClient(app) as client:
            response = client.get("/admin/dashboard")

        self.assertEqual(response.status_code, 200)
        self.assertIn("cachyos:'C'", response.text)
        self.assertIn(".distro-cachyos{", response.text)

    def test_other_distributions_remain_supported(self):
        with TestClient(app) as client:
            page = client.get("/admin/dashboard").text

        for entry in ("arch:'A'", "debian:'D'", "ubuntu:'U'", "fedora:'F'"):
            with self.subTest(entry=entry):
                self.assertIn(entry, page)

        self.assertIn("logos[distro]||'L'", page)


if __name__ == "__main__":
    unittest.main()
