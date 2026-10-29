"""Read-only admin inventory integration and authorization tests."""
import hashlib
import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient
from main import app
import agent_registry


class AdminInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / "agents.db"
        db_patch = patch.object(agent_registry, "DB_PATH", self.db)
        db_patch.start()
        self.addCleanup(db_patch.stop)
        token = "local-beta-admin"
        env_patch = patch.dict(os.environ, {
            "ARBY_ADMIN_TOKEN_HASH": hashlib.sha256(token.encode()).hexdigest(),
        })
        env_patch.start()
        self.addCleanup(env_patch.stop)
        self.headers = {"Authorization": "Bearer " + token}
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_requires_admin_even_when_database_missing(self):
        self.assertEqual(self.client.get("/api/v1/admin/agents").status_code, 401)
        self.assertEqual(self.client.get("/api/v1/admin/agents",
                         headers={"Authorization": "Bearer invalid"}).status_code, 401)
        response = self.client.get("/api/v1/admin/agents", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"agents": [], "count": 0})
        self.assertFalse(self.db.exists())

    def test_pending_approved_revoked_and_latest_scan(self):
        agent_registry.initialize_database()
        ids = [str(uuid4()) for _ in range(3)]
        for index, agent_id in enumerate(ids):
            agent_registry.register_agent("node-" + str(index), "arch", agent_id)
        self.assertTrue(agent_registry.approve_agent(ids[1]))
        self.assertTrue(agent_registry.approve_agent(ids[2]))
        self.assertTrue(agent_registry.revoke_agent(ids[2]))
        with closing(sqlite3.connect(self.db)) as db, db:
            db.execute("INSERT INTO scan_reports(agent_id,timestamp,status,count,packages_json) VALUES (?,?,?,?,?)",
                       (ids[1], "2026-01-01T00:00:00Z", "success", 5, "[]"))
            db.execute("INSERT INTO scan_reports(agent_id,timestamp,status,count,packages_json) VALUES (?,?,?,?,?)",
                       (ids[1], "2026-01-02T00:00:00Z", "success", 2, "[]"))
        response = self.client.get("/api/v1/admin/agents", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 3)
        self.assertEqual([a["status"] for a in data["agents"]],
                         ["pending", "approved", "revoked"])
        self.assertEqual(data["agents"][1]["updates"], 2)
        self.assertEqual(data["agents"][1]["scan_status"], "success")
        self.assertIsNone(data["agents"][0]["updates"])
        self.assertNotIn("token_hash", str(data))
        self.assertNotIn("packages_json", str(data))

    def test_missing_schema_returns_unavailable(self):
        with closing(sqlite3.connect(self.db)):
            pass
        response = self.client.get("/api/v1/admin/agents", headers=self.headers)
        self.assertEqual(response.status_code, 503)

    def test_ui_exposes_read_only_inventory(self):
        response = self.client.get("/admin/settings")
        self.assertEqual(response.status_code, 200)
        self.assertIn('id="agents"', response.text)
        self.assertIn('/api/v1/admin/agents', response.text)
        self.assertIn('Read-only agent inventory loaded.', response.text)


if __name__ == "__main__":
    unittest.main()
