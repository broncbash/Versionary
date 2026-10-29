"""Verify agent endpoints are reachable through the main application."""

import unittest

from fastapi.testclient import TestClient
from main import app


class TestMainIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()

    def test_agent_status(self):
        response = self.client.get("/api/v1/agents/status")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["service"],
            "ARBY PATCH COMMAND Agent API",
        )

    def test_registration_route_exists(self):
        response = self.client.post("/api/v1/agents/register")
        self.assertEqual(response.status_code, 422)

    def test_approval_requires_admin(self):
        response = self.client.post(
            "/api/v1/agents/not-a-uuid/approve"
        )
        self.assertEqual(response.status_code, 401)

    def test_revocation_requires_admin(self):
        response = self.client.post(
            "/api/v1/agents/not-a-uuid/revoke"
        )
        self.assertEqual(response.status_code, 401)

    def test_credential_requires_admin(self):
        response = self.client.post(
            "/api/v1/agents/not-a-uuid/credential"
        )
        self.assertEqual(response.status_code, 401)

    def test_heartbeat_route_exists(self):
        response = self.client.post(
            "/api/v1/agents/not-a-uuid/heartbeat"
        )
        self.assertEqual(response.status_code, 422)

    def test_report_route_exists(self):
        response = self.client.post(
            "/api/v1/agents/not-a-uuid/report",
            json={"status": "success", "packages": []},
        )
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
