"""Integration tests for administrator-only credential issuance."""

import hashlib
import os
import tempfile
import unittest

from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

import agent_registry as registry
from agent_enrollment_api import router


class TestAgentEnrollmentAPI(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "agents.db"

        self.db_patch = patch.object(
            registry, "DB_PATH", self.db_path
        )
        self.db_patch.start()

        self.admin_token = "unit-test-admin-token"
        self.admin_hash = hashlib.sha256(
            self.admin_token.encode()
        ).hexdigest()

        self.env_patch = patch.dict(
            os.environ,
            {"ARBY_ADMIN_TOKEN_HASH": self.admin_hash},
        )
        self.env_patch.start()

        registry.initialize_database()

        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.env_patch.stop()
        self.db_patch.stop()
        self.temp.cleanup()

    def create_agent(self, approved=False, revoked=False):
        agent_id = registry.register_agent(
            "test-agent", "arch"
        )

        if approved or revoked:
            self.assertTrue(
                registry.approve_agent(agent_id)
            )

        if revoked:
            self.assertTrue(
                registry.revoke_agent(agent_id)
            )

        return agent_id

    def issue(self, agent_id, token=None):
        headers = (
            {}
            if token is None
            else {"Authorization": f"Bearer {token}"}
        )

        return self.client.post(
            f"/api/v1/agents/{agent_id}/credential",
            headers=headers,
        )

    def test_admin_issues_usable_credential(self):
        agent_id = self.create_agent(approved=True)
        response = self.issue(
            agent_id, self.admin_token
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json()["agent_id"], agent_id
        )
        self.assertTrue(
            registry.authenticate_agent(
                agent_id, response.json()["token"]
            )
        )

    def test_no_authentication(self):
        agent_id = self.create_agent(approved=True)

        self.assertEqual(
            self.issue(agent_id).status_code, 401
        )

        self.assertIsNotNone(
            registry.issue_agent_credential(agent_id)
        )

    def test_wrong_admin_token(self):
        agent_id = self.create_agent(approved=True)

        self.assertEqual(
            self.issue(
                agent_id, "wrong-token"
            ).status_code,
            401,
        )

    def test_pending_agent(self):
        agent_id = self.create_agent()

        self.assertEqual(
            self.issue(
                agent_id, self.admin_token
            ).status_code,
            409,
        )

    def test_revoked_agent(self):
        agent_id = self.create_agent(revoked=True)

        self.assertEqual(
            self.issue(
                agent_id, self.admin_token
            ).status_code,
            409,
        )

    def test_unknown_agent(self):
        self.assertEqual(
            self.issue(
                str(uuid4()), self.admin_token
            ).status_code,
            409,
        )

    def test_duplicate_issuance(self):
        agent_id = self.create_agent(approved=True)

        self.assertEqual(
            self.issue(
                agent_id, self.admin_token
            ).status_code,
            201,
        )

        self.assertEqual(
            self.issue(
                agent_id, self.admin_token
            ).status_code,
            409,
        )

    def test_invalid_uuid(self):
        self.assertEqual(
            self.issue(
                "not-a-uuid", self.admin_token
            ).status_code,
            422,
        )

    def test_no_configured_admin_secret(self):
        agent_id = self.create_agent(approved=True)

        with patch.dict(
            os.environ,
            {"ARBY_ADMIN_TOKEN_HASH": ""},
        ):
            self.assertEqual(
                self.issue(
                    agent_id, self.admin_token
                ).status_code,
                401,
            )


if __name__ == "__main__":
    unittest.main()
