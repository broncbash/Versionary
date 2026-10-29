"""Integration tests for authenticated heartbeat and reporting."""

import json
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
from agent_reporting_api import router


class TestAgentReportingAPI(unittest.TestCase):

    def setUp(self):
        self.reporting_patch = patch.dict(
            "os.environ",
            {"ARBY_AGENT_REPORTING_ENABLED": "true"},
        )
        self.reporting_patch.start()

        self.temp = tempfile.TemporaryDirectory()

        self.db_patch = patch.object(
            registry,
            "DB_PATH",
            Path(self.temp.name) / "agents.db",
        )
        self.db_patch.start()

        registry.initialize_database()

        self.agent_id = registry.register_agent(
            "test-agent", "arch"
        )
        registry.approve_agent(self.agent_id)

        self.token = registry.issue_agent_credential(
            self.agent_id
        )

        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.db_patch.stop()
        self.temp.cleanup()
        self.reporting_patch.stop()

    def post(self, endpoint, token=None, payload=None, agent_id=None):
        headers = (
            {}
            if token is None
            else {"Authorization": f"Bearer {token}"}
        )

        return self.client.post(
            f"/api/v1/agents/{agent_id or self.agent_id}/{endpoint}",
            headers=headers,
            **({"json": payload} if payload is not None else {}),
        )

    def reports(self):
        with closing(sqlite3.connect(registry.DB_PATH)) as db:
            return db.execute(
                "SELECT status, count, packages_json, error "
                "FROM scan_reports"
            ).fetchall()

    def last_seen(self):
        with closing(sqlite3.connect(registry.DB_PATH)) as db:
            return db.execute(
                "SELECT last_seen FROM agents WHERE id = ?",
                (self.agent_id,),
            ).fetchone()[0]

    def test_heartbeat_updates_last_seen(self):
        self.assertIsNone(self.last_seen())

        response = self.post("heartbeat", self.token)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertIsNotNone(self.last_seen())

    def test_heartbeat_missing_token(self):
        self.assertEqual(
            self.post("heartbeat").status_code, 401
        )
        self.assertIsNone(self.last_seen())

    def test_heartbeat_wrong_token(self):
        self.assertEqual(
            self.post("heartbeat", "wrong").status_code, 401
        )
        self.assertIsNone(self.last_seen())

    def test_heartbeat_revoked_agent(self):
        registry.revoke_agent(self.agent_id)

        self.assertEqual(
            self.post("heartbeat", self.token).status_code, 401
        )

    def test_heartbeat_unknown_agent(self):
        response = self.post(
            "heartbeat",
            self.token,
            agent_id=str(uuid4()),
        )
        self.assertEqual(response.status_code, 401)

    def test_report_records_packages(self):
        packages = [
            {
                "name": "linux",
                "installed": "6.11",
                "available": "6.12",
            }
        ]

        response = self.post(
            "report",
            self.token,
            {"status": "success", "packages": packages},
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "recorded")

        reports = self.reports()
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0][0], "success")
        self.assertEqual(reports[0][1], 1)
        self.assertEqual(
            json.loads(reports[0][2])[0]["name"], "linux"
        )

    def test_report_error(self):
        response = self.post(
            "report",
            self.token,
            {
                "status": "error",
                "packages": [],
                "error": "pacman unavailable",
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            self.reports()[0][3], "pacman unavailable"
        )

    def test_report_missing_token(self):
        response = self.post(
            "report",
            payload={"status": "success"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.reports(), [])

    def test_report_invalid_token(self):
        response = self.post(
            "report",
            "wrong",
            {"status": "success"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.reports(), [])

    def test_report_revoked_agent(self):
        registry.revoke_agent(self.agent_id)

        response = self.post(
            "report",
            self.token,
            {"status": "success"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.reports(), [])

    def test_report_invalid_status(self):
        response = self.post(
            "report",
            self.token,
            {"status": "unknown"},
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.reports(), [])

    def test_report_invalid_package(self):
        response = self.post(
            "report",
            self.token,
            {
                "status": "success",
                "packages": [{"name": 123}],
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.reports(), [])

    def test_report_too_many_packages(self):
        response = self.post(
            "report",
            self.token,
            {
                "status": "success",
                "packages": [{}] * 5001,
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.reports(), [])

    def test_invalid_agent_uuid(self):
        response = self.post(
            "heartbeat",
            self.token,
            agent_id="invalid-uuid",
        )

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
