"""Disposable integration tests for Versionary HTTPS beta."""

import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

import agent_registry
import versionary_https_beta as beta


class HTTPSBetaIntegrationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)

        root = Path(temp.name)
        state = root / "https-beta"
        state.mkdir(mode=0o700)

        token = state / "admin-token"
        token.write_text("disposable-integration-admin-token\n")
        token.chmod(0o600)

        patches = [
            patch.object(beta, "STATE", state),
            patch.object(beta, "AUTH", token),
            patch.object(beta, "DB", state / "agents.db"),
            patch.object(agent_registry, "DB_PATH", state / "agents.db"),
            patch.dict(os.environ, {}, clear=False),
        ]

        for item in patches:
            item.start()
            self.addCleanup(item.stop)

        self.app = beta.create_app()
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)

        self.admin_headers = {
            "Authorization": "Bearer disposable-integration-admin-token"
        }

    def test_health_identifies_nonproduction_beta(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["production"])

    def test_inventory_rejects_missing_admin_token(self):
        response = self.client.get("/api/v1/admin/agents")
        self.assertEqual(response.status_code, 401)

    def test_inventory_rejects_invalid_admin_token(self):
        response = self.client.get(
            "/api/v1/admin/agents",
            headers={"Authorization": "Bearer incorrect-token"},
        )
        self.assertEqual(response.status_code, 401)

    def test_inventory_accepts_valid_admin_token(self):
        response = self.client.get(
            "/api/v1/admin/agents",
            headers=self.admin_headers,
        )
        self.assertEqual(response.status_code, 200)

    def test_dashboard_page_is_available(self):
        response = self.client.get("/admin/dashboard")
        self.assertEqual(response.status_code, 200)

    def test_unknown_agent_cannot_heartbeat(self):
        os.environ["VERSIONARY_BETA_REPORTING"] = "true"
        self.app = beta.create_app()
        self.client.close()
        self.client = TestClient(self.app)
        response = self.client.post(
            f"/api/v1/agents/{uuid4()}/heartbeat",
            headers={"Authorization": "Bearer invalid-agent-token"},
        )
        self.assertEqual(response.status_code, 401)

    def test_unknown_agent_cannot_report(self):
        os.environ["VERSIONARY_BETA_REPORTING"] = "true"
        self.app = beta.create_app()
        self.client.close()
        self.client = TestClient(self.app)
        response = self.client.post(
            f"/api/v1/agents/{uuid4()}/report",
            headers={"Authorization": "Bearer invalid-agent-token"},
            json={"status": "success", "packages": [], "error": None},
        )
        self.assertEqual(response.status_code, 401)

    def test_enrollment_rejects_invalid_identity(self):
        os.environ["VERSIONARY_BETA_ENROLLMENT"] = "true"
        self.app = beta.create_app()
        self.client.close()
        self.client = TestClient(self.app)
        response = self.client.post(
            "/api/v2/agents/register",
            json={
                "agent_id": "not-a-uuid",
                "hostname": "disposable-agent",
                "platform": "arch",
                "public_key": "invalid-key",
            },
        )
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
