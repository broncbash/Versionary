"""Agent API integration tests with isolated SQLite and configuration."""

import hashlib
import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

import agent_registry as registry
from agent_api import router


class TestAgentAPI(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "agents.db"
        self.path_patch = patch.object(registry, "DB_PATH", self.db_path)
        self.path_patch.start()
        self.admin_token = "test-admin-token-only"
        admin_hash = hashlib.sha256(self.admin_token.encode()).hexdigest()
        self.env_patch = patch.dict(
            os.environ,
            {
                "ARBY_AGENT_REGISTRATION_ENABLED": "true",
                "ARBY_ADMIN_TOKEN_HASH": admin_hash,
            },
        )
        self.env_patch.start()
        registry.initialize_database()
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.env_patch.stop()
        self.path_patch.stop()
        self.temp.cleanup()

    def admin_headers(self, token=None):
        return {"Authorization": f"Bearer {token or self.admin_token}"}

    def create_agent(self, hostname="arch-test"):
        agent_id = str(uuid4())
        registry.register_agent(
            hostname=hostname, platform="arch", agent_id=agent_id
        )
        return agent_id

    def registration_payload(self, agent_id=None, **overrides):
        payload = {
            "hostname": "arch-test",
            "platform": "arch",
            "agent_id": agent_id or str(uuid4()),
        }
        payload.update(overrides)
        return payload

    def test_status_endpoint(self):
        response = self.client.get("/api/v1/agents/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "development")
        self.assertTrue(data["registration_enabled"])
        self.assertFalse(data["reporting_enabled"])

    def test_status_reports_registration_disabled(self):
        with patch.dict(
            os.environ, {"ARBY_AGENT_REGISTRATION_ENABLED": "false"}
        ):
            response = self.client.get("/api/v1/agents/status")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["registration_enabled"])
        self.assertFalse(response.json()["reporting_enabled"])

    def test_registration_creates_pending_agent(self):
        agent_id = str(uuid4())
        response = self.client.post(
            "/api/v1/agents/register",
            json=self.registration_payload(agent_id),
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), {
            "agent_id": agent_id, "status": "pending"
        })
        self.assertFalse(registry.is_agent_approved(agent_id))
        with closing(sqlite3.connect(self.db_path)) as db:
            row = db.execute(
                "SELECT hostname, platform, status FROM agents WHERE id = ?",
                (agent_id,),
            ).fetchone()
        self.assertEqual(row, ("arch-test", "arch", "pending"))

    def test_invalid_registration_rejected(self):
        response = self.client.post(
            "/api/v1/agents/register",
            json=self.registration_payload(agent_id="invalid-uuid"),
        )
        self.assertEqual(response.status_code, 422)

    def test_reporting_not_available(self):
        response = self.client.post("/api/v1/agents/report")
        self.assertEqual(response.status_code, 404)

    def test_duplicate_registration_returns_409(self):
        payload = self.registration_payload()
        first = self.client.post("/api/v1/agents/register", json=payload)
        second = self.client.post("/api/v1/agents/register", json=payload)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(
            second.json()["detail"], "Agent identity already registered"
        )

    def test_blank_hostname_returns_422(self):
        response = self.client.post(
            "/api/v1/agents/register",
            json=self.registration_payload(hostname="   "),
        )
        self.assertEqual(response.status_code, 422)

    def test_blank_platform_returns_422(self):
        response = self.client.post(
            "/api/v1/agents/register",
            json=self.registration_payload(platform="   "),
        )
        self.assertEqual(response.status_code, 422)

    def test_registration_disabled_returns_503(self):
        with patch.dict(
            os.environ, {"ARBY_AGENT_REGISTRATION_ENABLED": "false"}
        ):
            response = self.client.post(
                "/api/v1/agents/register",
                json=self.registration_payload(),
            )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json()["detail"], "Agent registration is disabled"
        )
        with closing(sqlite3.connect(self.db_path)) as db:
            count = db.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
        self.assertEqual(count, 0)

    def test_approval_requires_admin_authentication(self):
        agent_id = self.create_agent()
        response = self.client.post(f"/api/v1/agents/{agent_id}/approve")
        self.assertEqual(response.status_code, 401)
        self.assertFalse(registry.is_agent_approved(agent_id))

    def test_admin_can_approve_pending_agent(self):
        agent_id = self.create_agent()
        response = self.client.post(
            f"/api/v1/agents/{agent_id}/approve",
            headers=self.admin_headers(),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "agent_id": agent_id, "status": "approved"
        })
        self.assertTrue(registry.is_agent_approved(agent_id))

    def test_invalid_admin_token_cannot_approve(self):
        agent_id = self.create_agent()
        response = self.client.post(
            f"/api/v1/agents/{agent_id}/approve",
            headers=self.admin_headers("wrong-token"),
        )
        self.assertEqual(response.status_code, 401)
        self.assertFalse(registry.is_agent_approved(agent_id))

    def test_repeat_approval_rejected(self):
        agent_id = self.create_agent()
        url = f"/api/v1/agents/{agent_id}/approve"
        first = self.client.post(url, headers=self.admin_headers())
        second = self.client.post(url, headers=self.admin_headers())
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 409)
        self.assertTrue(registry.is_agent_approved(agent_id))

    def test_invalid_approval_uuid_returns_422(self):
        response = self.client.post(
            "/api/v1/agents/not-a-uuid/approve",
            headers=self.admin_headers(),
        )
        self.assertEqual(response.status_code, 422)

    def test_unknown_agent_cannot_be_approved(self):
        response = self.client.post(
            f"/api/v1/agents/{uuid4()}/approve",
            headers=self.admin_headers(),
        )
        self.assertEqual(response.status_code, 409)

    def test_revocation_requires_admin_authentication(self):
        agent_id = self.create_agent()
        registry.approve_agent(agent_id)
        response = self.client.post(f"/api/v1/agents/{agent_id}/revoke")
        self.assertEqual(response.status_code, 401)
        self.assertTrue(registry.is_agent_approved(agent_id))

    def test_invalid_admin_token_cannot_revoke(self):
        agent_id = self.create_agent()
        registry.approve_agent(agent_id)
        response = self.client.post(
            f"/api/v1/agents/{agent_id}/revoke",
            headers=self.admin_headers("wrong-token"),
        )
        self.assertEqual(response.status_code, 401)
        self.assertTrue(registry.is_agent_approved(agent_id))

    def test_admin_can_revoke_approved_agent(self):
        agent_id = self.create_agent()
        registry.approve_agent(agent_id)
        response = self.client.post(
            f"/api/v1/agents/{agent_id}/revoke",
            headers=self.admin_headers(),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "agent_id": agent_id, "status": "revoked"
        })
        self.assertFalse(registry.is_agent_approved(agent_id))
        with closing(sqlite3.connect(self.db_path)) as db:
            status = db.execute(
                "SELECT status FROM agents WHERE id = ?", (agent_id,)
            ).fetchone()[0]
        self.assertEqual(status, "revoked")

    def test_repeat_revocation_rejected(self):
        agent_id = self.create_agent()
        registry.approve_agent(agent_id)
        url = f"/api/v1/agents/{agent_id}/revoke"
        first = self.client.post(url, headers=self.admin_headers())
        second = self.client.post(url, headers=self.admin_headers())
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 409)

    def test_revoked_agent_cannot_be_reapproved(self):
        agent_id = self.create_agent()
        registry.approve_agent(agent_id)
        revoke = self.client.post(
            f"/api/v1/agents/{agent_id}/revoke",
            headers=self.admin_headers(),
        )
        approve = self.client.post(
            f"/api/v1/agents/{agent_id}/approve",
            headers=self.admin_headers(),
        )
        self.assertEqual(revoke.status_code, 200)
        self.assertEqual(approve.status_code, 409)
        self.assertFalse(registry.is_agent_approved(agent_id))

    def test_invalid_revocation_uuid_returns_422(self):
        response = self.client.post(
            "/api/v1/agents/not-a-uuid/revoke",
            headers=self.admin_headers(),
        )
        self.assertEqual(response.status_code, 422)

    def test_unknown_agent_cannot_be_revoked(self):
        response = self.client.post(
            f"/api/v1/agents/{uuid4()}/revoke",
            headers=self.admin_headers(),
        )
        self.assertEqual(response.status_code, 409)


if __name__ == "__main__":
    unittest.main()

