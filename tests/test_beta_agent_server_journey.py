from contextlib import closing
"""Disposable in-process beta journey: enrollment, approval, reporting, revocation.

No sockets, hosted infrastructure, production database, or live container access.
The agent's HTTP transport is replaced with a FastAPI TestClient adapter.
"""
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

import agent_registry
from agent.credentials import load_credential
from agent.enrollment_client import complete_v2, register_v2
from agent.enrollment_journal import load_journal
from agent.reporting import validate_report
from enrollment_v2_api import router as enrollment_router
from agent_reporting_api import router as reporting_router


class BetaAgentServerJourney(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.state = root / "agent-state"
        self.state.mkdir(mode=0o700)
        self.key = self.state / "key.json"
        self.journal = self.state / "journal.json"
        self.credential = self.state / "credential.json"
        self.db = root / "agents.db"
        db_patch = patch.object(agent_registry, "DB_PATH", self.db)
        db_patch.start()
        self.addCleanup(db_patch.stop)
        env_patch = patch.dict(os.environ, {
            "ARBY_ENROLLMENT_V2_ENABLED": "true",
            "ARBY_AGENT_REPORTING_ENABLED": "true",
            "ARBY_SETTINGS_RUNTIME_ENABLED": "false",
        })
        env_patch.start()
        self.addCleanup(env_patch.stop)
        agent_registry.initialize_database()
        app = FastAPI()
        app.include_router(enrollment_router)
        app.include_router(reporting_router)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.identity = {
            "agent_id": str(uuid4()), "hostname": "disposable-beta",
            "platform": "arch",
        }

    def post(self, path, payload):
        response = self.client.post(path, json=payload)
        if response.status_code >= 400:
            raise RuntimeError(f"test server rejected {path}: {response.status_code}")
        return response.json()

    def enroll(self):
        registration = register_v2(self.identity, key_path=self.key, post=self.post)
        self.assertEqual(registration["status"], "pending")
        self.assertTrue(agent_registry.approve_agent(self.identity["agent_id"]))
        result = complete_v2(
            self.identity, key_path=self.key, journal_path=self.journal,
            credential_path=self.credential, post=self.post,
        )
        self.assertEqual(result["status"], "enrolled")
        self.assertFalse(result["recovered"])
        self.assertIsNone(load_journal(self.journal))
        return load_credential(self.credential)

    def report(self, token):
        report = {"status": "success", "packages": [
            {"name": "sample-package", "installed": "1.0",
             "available": "1.1", "repository": "core"}
        ], "error": None}
        return self.client.post(
            f"/api/v1/agents/{self.identity['agent_id']}/report",
            content=validate_report(report),
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/json"},
        )

    def test_full_disposable_journey_and_revocation(self):
        token = self.enroll()
        self.assertTrue(agent_registry.authenticate_agent(self.identity["agent_id"], token))
        heartbeat = self.client.post(
            f"/api/v1/agents/{self.identity['agent_id']}/heartbeat",
            headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(heartbeat.status_code, 200, heartbeat.text)
        recorded = self.report(token)
        self.assertEqual(recorded.status_code, 201, recorded.text)
        with closing(sqlite3.connect(self.db)) as db:
            status, count, packages = db.execute(
                "SELECT status, count, packages_json FROM scan_reports "
                "WHERE agent_id = ?", (self.identity["agent_id"],)
            ).fetchone()
        self.assertEqual(status, "success")
        self.assertEqual(count, 1)
        self.assertEqual(json.loads(packages)[0]["name"], "sample-package")
        self.assertTrue(agent_registry.revoke_agent(self.identity["agent_id"]))
        self.assertFalse(agent_registry.authenticate_agent(self.identity["agent_id"], token))
        self.assertEqual(self.report(token).status_code, 401)

    def test_pending_agent_cannot_report(self):
        register_v2(self.identity, key_path=self.key, post=self.post)
        self.assertEqual(self.report("unapproved-token").status_code, 401)

    def test_disabled_enrollment_stays_closed(self):
        with patch.dict(os.environ, {"ARBY_ENROLLMENT_V2_ENABLED": "false"}):
            with self.assertRaisesRegex(RuntimeError, "503"):
                register_v2(self.identity, key_path=self.key, post=self.post)
        with closing(sqlite3.connect(self.db)) as db:
            self.assertIsNone(db.execute(
                "SELECT id FROM agents WHERE id = ?",
                (self.identity["agent_id"],)
            ).fetchone())

    def test_lost_completion_response_recovers_without_duplicate_token(self):
        register_v2(self.identity, key_path=self.key, post=self.post)
        self.assertTrue(agent_registry.approve_agent(self.identity["agent_id"]))
        def lost_reply(path, payload):
            response = self.post(path, payload)
            if path.endswith("/complete"):
                raise ConnectionError("simulated dropped completion response")
            return response
        with self.assertRaisesRegex(ConnectionError, "dropped"):
            complete_v2(
                self.identity, key_path=self.key, journal_path=self.journal,
                credential_path=self.credential, post=lost_reply)
        self.assertIsNotNone(load_journal(self.journal))
        recovered = complete_v2(
            self.identity, key_path=self.key, journal_path=self.journal,
            credential_path=self.credential, post=self.post)
        self.assertTrue(recovered["recovered"])
        self.assertIsNone(load_journal(self.journal))
        token = load_credential(self.credential)
        self.assertTrue(agent_registry.authenticate_agent(self.identity["agent_id"], token))
        self.assertEqual(self.report(token).status_code, 201)
        with closing(sqlite3.connect(self.db)) as db:
            count = db.execute("SELECT COUNT(*) FROM agent_credentials WHERE agent_id = ?",
                               (self.identity["agent_id"],)).fetchone()[0]
        self.assertEqual(count, 1)

    def test_rejected_unapproved_completion_does_not_create_credential(self):
        register_v2(self.identity, key_path=self.key, post=self.post)
        with self.assertRaisesRegex(RuntimeError, "409"):
            complete_v2(
                self.identity, key_path=self.key, journal_path=self.journal,
                credential_path=self.credential, post=self.post)
        self.assertFalse(self.credential.exists())
        self.assertIsNone(load_journal(self.journal))

    def test_disabled_reporting_rejects_enrolled_agent(self):
        token = self.enroll()
        with patch.dict(os.environ, {"ARBY_AGENT_REPORTING_ENABLED": "false"}):
            self.assertEqual(self.report(token).status_code, 503)


if __name__ == "__main__":
    unittest.main()
