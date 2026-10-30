"""Isolated real API flow; no installed agent, no network, no host database."""
import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

import agent_registry
from admin_agents_api import router as inventory_router
from agent_enrollment_api import router as credential_router
from agent_reporting_api import router as reporting_router


class VersionaryLiveFlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="versionary-api-test-")
        self.addCleanup(self.tmp.cleanup)
        self.db_patch = patch.object(agent_registry, "DB_PATH", Path(self.tmp.name) / "agents.db")
        self.db_patch.start()
        self.addCleanup(self.db_patch.stop)
        admin_token = "versionary-local-test-admin-token"
        self.admin_token = admin_token
        env = {
            "ARBY_ADMIN_TOKEN_HASH": hashlib.sha256(admin_token.encode()).hexdigest(),
            "ARBY_AGENT_REPORTING_ENABLED": "true",
            "ARBY_SETTINGS_RUNTIME_ENABLED": "false",
        }
        self.env_patch = patch.dict(os.environ, env)
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)
        agent_registry.initialize_database()
        app = FastAPI()
        app.include_router(credential_router)
        app.include_router(reporting_router)
        app.include_router(inventory_router)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def admin_headers(self):
        return {"Authorization": "Bearer " + self.admin_token}

    def test_authenticated_report_reaches_real_inventory(self):
        agent_id = agent_registry.register_agent("versionary-test-arch", "arch")
        inventory = self.client.get("/api/v1/admin/agents", headers=self.admin_headers())
        self.assertEqual(inventory.status_code, 200)
        self.assertEqual(inventory.json()["agents"][0]["status"], "pending")
        denied = self.client.post(f"/api/v1/agents/{agent_id}/credential", headers=self.admin_headers())
        self.assertEqual(denied.status_code, 409)
        self.assertTrue(agent_registry.approve_agent(agent_id))
        issued = self.client.post(f"/api/v1/agents/{agent_id}/credential", headers=self.admin_headers())
        self.assertEqual(issued.status_code, 201)
        token = issued.json()["token"]
        agent_headers = {"Authorization": "Bearer " + token}
        heartbeat = self.client.post(f"/api/v1/agents/{agent_id}/heartbeat", headers=agent_headers)
        self.assertEqual(heartbeat.status_code, 200)
        packages = [{"name": "linux", "installed": "6.1", "available": "6.2"}]
        report = self.client.post(f"/api/v1/agents/{agent_id}/report", headers=agent_headers,
                                  json={"status": "success", "packages": packages})
        self.assertEqual(report.status_code, 201)
        inventory = self.client.get("/api/v1/admin/agents", headers=self.admin_headers())
        self.assertEqual(inventory.status_code, 200)
        row = inventory.json()["agents"][0]
        self.assertEqual(row["hostname"], "versionary-test-arch")
        self.assertEqual(row["status"], "approved")
        self.assertEqual(row["health"], "online")
        self.assertEqual(row["scan_status"], "success")
        self.assertEqual(row["updates"], 1)
        self.assertIsNotNone(row["last_seen"])
        self.assertNotIn("token", row)
        self.assertNotIn("token_hash", row)

    def test_wrong_credentials_and_revocation_are_enforced(self):
        agent_id = agent_registry.register_agent("test-debian", "debian")
        self.assertTrue(agent_registry.approve_agent(agent_id))
        issued = self.client.post(f"/api/v1/agents/{agent_id}/credential", headers=self.admin_headers())
        self.assertEqual(issued.status_code, 201)
        token = issued.json()["token"]
        self.assertEqual(self.client.get("/api/v1/admin/agents").status_code, 401)
        self.assertEqual(self.client.post(f"/api/v1/agents/{agent_id}/heartbeat",
                                          headers={"Authorization": "Bearer wrong"}).status_code, 401)
        self.assertTrue(agent_registry.revoke_agent(agent_id))
        self.assertEqual(self.client.post(f"/api/v1/agents/{agent_id}/heartbeat",
                                          headers={"Authorization": "Bearer " + token}).status_code, 401)
        inventory = self.client.get("/api/v1/admin/agents", headers=self.admin_headers())
        self.assertEqual(inventory.json()["agents"][0]["health"], "revoked")

    def test_reporting_is_disabled_by_default(self):
        agent_id = agent_registry.register_agent("test-fedora", "fedora")
        self.assertTrue(agent_registry.approve_agent(agent_id))
        token = agent_registry.issue_agent_credential(agent_id)
        with patch.dict(os.environ, {"ARBY_AGENT_REPORTING_ENABLED": "false"}):
            result = self.client.post(f"/api/v1/agents/{agent_id}/heartbeat",
                                      headers={"Authorization": "Bearer " + token})
        self.assertEqual(result.status_code, 503)


if __name__ == "__main__":
    unittest.main()
