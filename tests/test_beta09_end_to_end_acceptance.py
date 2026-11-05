"""Real FastAPI + isolated SQLite beta lifecycle; no network or deployment."""
import hashlib
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient
import agent_registry
from main import app


class Beta09EndToEndAcceptance(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="versionary-e2e-")
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / "agents.db"
        self.db_patch = patch.object(agent_registry, "DB_PATH", self.db)
        self.db_patch.start()
        self.addCleanup(self.db_patch.stop)
        self.admin = "disposable-beta09-admin-token"
        self.env_patch = patch.dict(os.environ, {
            "ARBY_ADMIN_TOKEN_HASH": hashlib.sha256(self.admin.encode()).hexdigest(),
            "ARBY_AGENT_REGISTRATION_ENABLED": "true",
            "ARBY_AGENT_REPORTING_ENABLED": "true",
            "ARBY_SETTINGS_RUNTIME_ENABLED": "false",
        })
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)
        agent_registry.initialize_database()
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.agent_id = str(uuid4())
        self.base = f"/api/v1/agents/{self.agent_id}"
        self.admin_headers = {"Authorization": "Bearer " + self.admin}

    def register(self):
        response = self.client.post("/api/v1/agents/register", json={
            "agent_id": self.agent_id, "hostname": "disposable-beta09", "platform": "arch",
        })
        self.assertEqual(response.status_code, 201, response.text)

    def approve_and_credential(self):
        self.register()
        response = self.client.post(self.base + "/approve", headers=self.admin_headers)
        self.assertEqual(response.status_code, 200, response.text)
        token = agent_registry.issue_agent_credential(self.agent_id)
        self.assertTrue(token)
        return {"Authorization": "Bearer " + token}

    def test_pending_agent_visible_but_cannot_report(self):
        self.register()
        inventory = self.client.get("/api/v1/admin/agents", headers=self.admin_headers)
        self.assertEqual(inventory.status_code, 200)
        self.assertEqual(inventory.json()["agents"][0]["status"], "pending")
        denied = self.client.post(self.base + "/heartbeat")
        self.assertEqual(denied.status_code, 401)

    def test_approved_agent_heartbeat_report_and_dashboard_inventory(self):
        headers = self.approve_and_credential()
        heartbeat = self.client.post(self.base + "/heartbeat", headers=headers)
        self.assertEqual(heartbeat.status_code, 200, heartbeat.text)
        report = self.client.post(self.base + "/report", headers=headers,
                                  json={"status": "success", "packages": []})
        self.assertEqual(report.status_code, 201, report.text)
        inventory = self.client.get("/api/v1/admin/agents", headers=self.admin_headers)
        self.assertEqual(inventory.status_code, 200, inventory.text)
        row = inventory.json()["agents"][0]
        self.assertEqual(row["status"], "approved")
        self.assertEqual(row["health"], "online")
        self.assertEqual(row["updates"], 0)
        self.assertEqual(row["scan_status"], "success")
        dashboard = self.client.get("/admin/dashboard")
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn("Versionary", dashboard.text)
        self.assertNotIn(headers["Authorization"].split(" ", 1)[1], dashboard.text)
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM scan_reports").fetchone()[0], 1)

    def test_revocation_blocks_future_heartbeats_and_reports(self):
        headers = self.approve_and_credential()
        revoke = self.client.post(self.base + "/revoke", headers=self.admin_headers)
        self.assertEqual(revoke.status_code, 200)
        self.assertEqual(self.client.post(self.base + "/heartbeat", headers=headers).status_code, 401)
        self.assertEqual(self.client.post(self.base + "/report", headers=headers,
                                     json={"status": "success", "packages": []}).status_code, 401)
        inventory = self.client.get("/api/v1/admin/agents", headers=self.admin_headers).json()
        self.assertEqual(inventory["agents"][0]["health"], "revoked")

    def test_disabled_reporting_gate_blocks_valid_credential(self):
        headers = self.approve_and_credential()
        with patch.dict(os.environ, {"ARBY_AGENT_REPORTING_ENABLED": "false"}):
            response = self.client.post(self.base + "/heartbeat", headers=headers)
        self.assertEqual(response.status_code, 503)

    def test_inventory_requires_admin_and_does_not_expose_credential(self):
        headers = self.approve_and_credential()
        self.assertEqual(self.client.get("/api/v1/admin/agents").status_code, 401)
        result = self.client.get("/api/v1/admin/agents", headers=self.admin_headers)
        self.assertEqual(result.status_code, 200)
        self.assertNotIn(headers["Authorization"].split(" ", 1)[1], result.text)
        self.assertNotIn("token_hash", result.text)


if __name__ == "__main__":
    unittest.main()
