"""Fleet dashboard filtering and read-only usability contract."""
import unittest
from fastapi.testclient import TestClient
from main import app


class FleetControlsTests(unittest.TestCase):
    def test_fleet_filters_and_sort_controls(self):
        with TestClient(app) as client:
            response = client.get("/admin/dashboard")
        page = response.text
        for control in ('id="search"', 'id="status-filter"', 'id="sort"', 'id="results"'):
            with self.subTest(control=control):
                self.assertIn(control, page)
        self.assertIn("Showing '+selected.length+' of '+agents.length+' agents", page)

    def test_filtering_is_client_side_and_keeps_full_inventory(self):
        with TestClient(app) as client:
            page = client.get("/admin/dashboard").text
        self.assertIn("let inventory=[]", page)
        self.assertIn("inventory=data.agents", page)
        self.assertIn("render(inventory)", page)
        self.assertIn("selected=agents.filter", page)
        self.assertIn("selected.sort", page)

    def test_no_mutating_endpoints_or_unsafe_html(self):
        with TestClient(app) as client:
            page = client.get("/admin/dashboard").text
        self.assertIn("element.textContent=text", page)
        self.assertNotIn("innerHTML", page)
        self.assertNotIn("localStorage", page)
        self.assertNotIn("sessionStorage", page)
        self.assertIn("method:'POST'", page)
        self.assertIn("window.confirm(warning)", page)
        self.assertIn("Authorization:'Bearer '+actionCredential", page)
        self.assertIn("const actionCredential=credential", page)
        self.assertIn("Authorization:'Bearer '+requestCredential", page)
        self.assertIn("const requestCredential=credential", page)
        self.assertIn("encodeURIComponent(agent.id)", page)
        self.assertIn("credentials:'omit'", page)
        self.assertIn("PERMANENTLY revoke", page)
        self.assertNotIn("method:'PATCH'", page)


if __name__ == "__main__":
    unittest.main()
