"""Regression tests for agent API feature switches."""

import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent_api import router as registration_router
from agent_feature_flags import (
    registration_enabled,
    reporting_enabled,
)
from agent_reporting_api import router as reporting_router


class TestAgentFeatureFlags(unittest.TestCase):

    def test_disabled_by_default(self):
        with patch.dict("os.environ", {
            "ARBY_AGENT_REGISTRATION_ENABLED": "",
            "ARBY_AGENT_REPORTING_ENABLED": "",
        }):
            self.assertFalse(registration_enabled())
            self.assertFalse(reporting_enabled())

    def test_independent_flags(self):
        with patch.dict("os.environ", {
            "ARBY_AGENT_REGISTRATION_ENABLED": "true",
            "ARBY_AGENT_REPORTING_ENABLED": "false",
        }):
            self.assertTrue(registration_enabled())
            self.assertFalse(reporting_enabled())

    def test_reporting_endpoints_disabled(self):
        app = FastAPI()
        app.include_router(reporting_router)

        with patch.dict(
            "os.environ",
            {"ARBY_AGENT_REPORTING_ENABLED": "false"},
        ):
            with TestClient(app) as client:
                agent_id = "00000000-0000-4000-8000-000000000000"

                for endpoint in ("heartbeat", "report"):
                    response = client.post(
                        f"/api/v1/agents/{agent_id}/{endpoint}",
                        json={"status": "success", "packages": []},
                    )
                    self.assertEqual(response.status_code, 503)

    def test_status_reflects_reporting_flag(self):
        app = FastAPI()
        app.include_router(registration_router)

        with patch.dict(
            "os.environ",
            {"ARBY_AGENT_REPORTING_ENABLED": "true"},
        ):
            with TestClient(app) as client:
                response = client.get("/api/v1/agents/status")
                self.assertEqual(response.status_code, 200)
                self.assertTrue(
                    response.json()["reporting_enabled"]
                )


if __name__ == "__main__":
    unittest.main()
