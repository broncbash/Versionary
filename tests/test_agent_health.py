"""Heartbeat health classification and dashboard presentation contract."""
import unittest
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from admin_agents_api import agent_health
from main import app


class AgentHealthTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 29, 12, 0, tzinfo=timezone.utc)

    def test_online_and_boundary(self):
        self.assertEqual(agent_health("approved", (self.now - timedelta(minutes=5)).isoformat(), self.now), "online")
        self.assertEqual(agent_health("approved", (self.now - timedelta(minutes=30)).isoformat(), self.now), "online")

    def test_stale(self):
        self.assertEqual(agent_health("approved", (self.now - timedelta(minutes=31)).isoformat(), self.now), "stale")

    def test_missing_or_invalid_contact_never_online(self):
        for value, expected in [(None, "no_contact"), ("", "no_contact"), ("bad", "unknown"),
                                ("2026-10-29T11:00:00", "unknown"),
                                ((self.now + timedelta(minutes=1)).isoformat(), "unknown")]:
            with self.subTest(value=value):
                self.assertEqual(agent_health("approved", value, self.now), expected)

    def test_lifecycle_overrides_heartbeat(self):
        for status in ("pending", "revoked"):
            with self.subTest(status=status):
                self.assertEqual(agent_health(status, self.now.isoformat(), self.now), status)

    def test_dashboard_explains_health_and_scan_failure(self):
        with TestClient(app) as client:
            page = client.get("/admin/dashboard").text
        self.assertIn('id="online"', page)
        self.assertIn('id="attention"', page)
        self.assertIn("Latest scan failed", page)
        self.assertIn("within 30 minutes", page)


if __name__ == "__main__":
    unittest.main()
