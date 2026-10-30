"""Regression tests for the isolated desktop demo."""

import unittest
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from desktop_demo import app, sample_fleet


class DesktopDemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_identifies_simulation(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["mode"],
            "simulated-desktop-demo",
        )
        self.assertFalse(response.json()["production"])

    def test_fleet_has_six_fictional_agents(self):
        response = self.client.get("/api/v1/admin/agents")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 6)

    def test_fleet_has_expected_health_states(self):
        agents = self.client.get(
            "/api/v1/admin/agents"
        ).json()["agents"]
        states = {agent["health"] for agent in agents}

        self.assertEqual(
            states,
            {
                "online",
                "stale",
                "pending",
                "revoked",
                "no_contact",
            },
        )

    def test_fleet_has_expected_approval_states(self):
        agents = self.client.get(
            "/api/v1/admin/agents"
        ).json()["agents"]
        states = {agent["status"] for agent in agents}

        self.assertEqual(
            states,
            {"approved", "pending", "revoked"},
        )

    def test_sample_timestamps_are_predictable(self):
        now = datetime(2026, 10, 30, tzinfo=timezone.utc)
        fleet = sample_fleet(now)
        self.assertEqual(fleet["count"], 6)
        self.assertEqual(
            fleet["agents"][0]["last_seen"],
            "2026-10-29T23:55:00+00:00",
        )

    def test_dashboard_loads(self):
        response = self.client.get("/admin/dashboard")
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "Patch Command",
            response.text,
        )

    def test_dashboard_automatically_refreshes(self):
        response = self.client.get("/admin/dashboard")
        self.assertIn(
            "document.getElementById('refresh').click()",
            response.text,
        )

    def test_dashboard_has_demo_credentials_only(self):
        response = self.client.get("/admin/dashboard")
        self.assertIn("demo-only", response.text)
        self.assertIn(
            "no token required",
            response.text,
        )

    def test_dashboard_hides_clear_access(self):
        response = self.client.get("/admin/dashboard")
        self.assertIn(
            'id="clear" type="button" disabled hidden',
            response.text,
        )

    def test_dashboard_has_security_headers(self):
        response = self.client.get("/admin/dashboard")
        self.assertEqual(
            response.headers["cache-control"],
            "no-store",
        )
        self.assertEqual(
            response.headers["x-frame-options"],
            "DENY",
        )
        self.assertIn(
            "default-src 'none'",
            response.headers["content-security-policy"],
        )

    def test_demo_has_no_mutation_endpoints(self):
        paths = {route.path for route in app.routes}
        self.assertEqual(
            paths,
            {
                "/openapi.json",
                "/health",
                "/api/v1/admin/agents",
                "/admin/dashboard",
            },
        )


if __name__ == "__main__":
    unittest.main()
