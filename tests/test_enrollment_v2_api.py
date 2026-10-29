"""Isolated integration tests for enrollment v2 HTTP routes."""

import hashlib
import os
import secrets
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

import agent_registry
from enrollment_crypto import generate_keypair
from enrollment_recoverable import sign_enrollment
from enrollment_v2_api import router


class TestEnrollmentV2API(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

        db_path = Path(self.temp.name) / "agents.db"
        db_patch = patch.object(
            agent_registry, "DB_PATH", db_path
        )
        db_patch.start()
        self.addCleanup(db_patch.stop)

        env_patch = patch.dict(
            os.environ,
            {"ARBY_ENROLLMENT_V2_ENABLED": "true"},
        )
        env_patch.start()
        self.addCleanup(env_patch.stop)

        agent_registry.initialize_database()

        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

        self.private_key, self.public_key = generate_keypair()
        self.agent_id = str(uuid4())

        self.payload = {
            "agent_id": self.agent_id,
            "hostname": "v2-test",
            "platform": "arch",
            "public_key": self.public_key,
        }

    def register(self):
        return self.client.post(
            "/api/v2/agents/register",
            json=self.payload,
        )

    def approve(self):
        self.assertEqual(self.register().status_code, 201)
        self.assertTrue(
            agent_registry.approve_agent(self.agent_id)
        )

    def challenge(self):
        return self.client.post(
            f"/api/v2/agents/{self.agent_id}/challenge"
        )

    def complete(self, challenge, token, private_key=None):
        credential_hash = hashlib.sha256(
            token.encode()
        ).hexdigest()

        signature = sign_enrollment(
            private_key or self.private_key,
            self.agent_id,
            challenge,
            credential_hash,
        )

        return self.client.post(
            f"/api/v2/agents/{self.agent_id}/complete",
            json={
                "challenge": challenge,
                "signature": signature,
                "credential_hash": credential_hash,
            },
        )

    def test_registration_pending(self):
        response = self.register()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "pending")

    def test_duplicate_registration(self):
        self.register()
        self.assertEqual(self.register().status_code, 409)

    def test_invalid_key(self):
        self.payload["public_key"] = "invalid"
        self.assertEqual(self.register().status_code, 422)

    def test_pending_cannot_get_challenge(self):
        self.register()
        self.assertEqual(self.challenge().status_code, 409)

    def test_approved_gets_challenge(self):
        self.approve()
        response = self.challenge()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["challenge"])

    def test_full_enrollment(self):
        self.approve()
        challenge = self.challenge().json()["challenge"]
        token = secrets.token_urlsafe(48)

        response = self.complete(challenge, token)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["recovered"])
        self.assertTrue(
            agent_registry.authenticate_agent(
                self.agent_id, token
            )
        )

    def test_lost_response_recovery(self):
        self.approve()
        challenge = self.challenge().json()["challenge"]
        token = secrets.token_urlsafe(48)

        first = self.complete(challenge, token)
        second = self.complete(challenge, token)

        self.assertFalse(first.json()["recovered"])
        self.assertTrue(second.json()["recovered"])

    def test_wrong_private_key(self):
        self.approve()
        challenge = self.challenge().json()["challenge"]
        token = secrets.token_urlsafe(48)
        other_private, _ = generate_keypair()

        response = self.complete(
            challenge, token, other_private
        )
        self.assertEqual(response.status_code, 409)

    def test_revoked_agent(self):
        self.approve()
        self.assertTrue(
            agent_registry.revoke_agent(self.agent_id)
        )
        self.assertEqual(self.challenge().status_code, 409)

    def test_disabled_by_default(self):
        with patch.dict(
            os.environ,
            {"ARBY_ENROLLMENT_V2_ENABLED": "false"},
        ):
            self.assertEqual(self.register().status_code, 503)

    def test_invalid_agent_uuid(self):
        response = self.client.post(
            "/api/v2/agents/not-a-uuid/challenge"
        )
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
