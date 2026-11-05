"""Security tests for HTTPS beta administrator routes."""

import os
import tempfile
import unittest

from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

import agent_registry
import versionary_https_beta as beta


class HTTPSBetaAdminTests(unittest.TestCase):

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)

        state = Path(temp.name) / "beta"
        state.mkdir(mode=0o700)

        token = state / "admin-token"
        token.write_text("disposable-admin-token\n")
        token.chmod(0o600)

        patches = [
            patch.object(beta, "STATE", state),
            patch.object(beta, "AUTH", token),
            patch.object(beta, "DB", state / "agents.db"),
            patch.object(
                agent_registry,
                "DB_PATH",
                state / "agents.db",
            ),
            patch.dict(os.environ, {}, clear=False),
        ]

        for item in patches:
            item.start()
            self.addCleanup(item.stop)

        self.client = TestClient(beta.create_app())
        self.addCleanup(self.client.close)

        self.agent_id = str(uuid4())
        self.approve_url = (
            f"/api/v1/admin/agents/{self.agent_id}/approve"
        )
        self.revoke_url = (
            f"/api/v1/admin/agents/{self.agent_id}/revoke"
        )

        self.headers = {
            "Authorization": "Bearer disposable-admin-token"
        }

    def test_approval_requires_admin_token(self):
        response = self.client.post(self.approve_url)
        self.assertEqual(response.status_code, 401)

    def test_approval_rejects_invalid_admin_token(self):
        response = self.client.post(
            self.approve_url,
            headers={"Authorization": "Bearer incorrect"},
        )
        self.assertEqual(response.status_code, 401)

    def test_revocation_requires_admin_token(self):
        response = self.client.post(self.revoke_url)
        self.assertEqual(response.status_code, 401)

    def test_unknown_agent_cannot_be_approved(self):
        response = self.client.post(
            self.approve_url,
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 409)

    def test_unknown_agent_cannot_be_revoked(self):
        response = self.client.post(
            self.revoke_url,
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 409)

    def test_legacy_registration_is_not_exposed(self):
        response = self.client.post(
            "/api/v1/agents/register",
            json={
                "agent_id": self.agent_id,
                "hostname": "disposable",
                "platform": "arch",
            },
        )
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
