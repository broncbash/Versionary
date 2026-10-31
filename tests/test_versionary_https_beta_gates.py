"""Feature-gate acceptance tests for isolated Versionary HTTPS beta."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

import agent_registry
import versionary_https_beta as beta


class HTTPSBetaGateTests(unittest.TestCase):

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)

        root = Path(temp.name)
        state = root / "beta"
        state.mkdir(mode=0o700)

        auth = state / "admin-token"
        auth.write_text("disposable-test-token\n")
        auth.chmod(0o600)

        patches = [
            patch.object(beta, "STATE", state),
            patch.object(beta, "AUTH", auth),
            patch.object(beta, "DB", state / "agents.db"),
            patch.object(agent_registry, "DB_PATH", state / "agents.db"),
            patch.dict(os.environ, {}, clear=False),
        ]

        for item in patches:
            item.start()
            self.addCleanup(item.stop)

        os.environ.pop("VERSIONARY_BETA_REPORTING", None)
        os.environ.pop("VERSIONARY_BETA_ENROLLMENT", None)

    def test_reporting_disabled_by_default(self):
        app = beta.create_app()

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/agents/{uuid4()}/heartbeat",
                headers={"Authorization": "Bearer invalid"},
            )

        self.assertEqual(response.status_code, 503)

    def test_enrollment_disabled_by_default(self):
        app = beta.create_app()

        with TestClient(app) as client:
            response = client.post(
                "/api/v2/agents/register",
                json={
                    "agent_id": str(uuid4()),
                    "hostname": "disposable",
                    "platform": "arch",
                    "public_key": "invalid",
                },
            )

        self.assertEqual(response.status_code, 503)

    def test_reporting_requires_exact_opt_in(self):
        os.environ["VERSIONARY_BETA_REPORTING"] = "TRUE"

        app = beta.create_app()

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/agents/{uuid4()}/heartbeat",
                headers={"Authorization": "Bearer invalid"},
            )

        self.assertEqual(response.status_code, 503)

    def test_reporting_enabled_explicitly(self):
        os.environ["VERSIONARY_BETA_REPORTING"] = "true"

        app = beta.create_app()

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/agents/{uuid4()}/heartbeat",
                headers={"Authorization": "Bearer invalid"},
            )

        self.assertEqual(response.status_code, 401)

    def test_enrollment_enabled_explicitly(self):
        os.environ["VERSIONARY_BETA_ENROLLMENT"] = "true"

        app = beta.create_app()

        with TestClient(app) as client:
            response = client.post(
                "/api/v2/agents/register",
                json={
                    "agent_id": "invalid",
                    "hostname": "disposable",
                    "platform": "arch",
                    "public_key": "invalid",
                },
            )

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
