"""Security regression matrix for opt-in agent feature gates.

All tests run against isolated temporary settings; no live agents are contacted.
"""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent_api import router as registration_router
from agent_reporting_api import router as reporting_router
from runtime_configuration import effective_flags
from server_settings import DEFAULTS


class AgentGateSecurityMatrixTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.settings = Path(self.temp.name) / "settings.json"
        self.data = {**DEFAULTS, "public_url": "https://patch.example.test",
                     "enrollment_enabled": True, "reporting_enabled": True}
        self.write_settings()
        self.env = {
            "ARBY_SETTINGS_PATH": str(self.settings),
            "ARBY_SETTINGS_RUNTIME_ENABLED": "true",
            "ARBY_AGENT_REGISTRATION_ENABLED": "true",
            "ARBY_AGENT_REPORTING_ENABLED": "true",
        }
        app = FastAPI()
        app.include_router(registration_router)
        app.include_router(reporting_router)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def write_settings(self):
        self.settings.write_text(json.dumps(self.data), encoding="utf-8")
        self.settings.chmod(0o600)

    def assert_both_disabled(self, env=None):
        with patch.dict(os.environ, env or self.env, clear=True):
            flags = effective_flags()
            self.assertFalse(flags["registration_enabled"])
            self.assertFalse(flags["reporting_enabled"])
            registration = self.client.post("/api/v1/agents/register", json={
                "agent_id": str(uuid4()), "hostname": "test", "platform": "arch"})
            self.assertEqual(registration.status_code, 503)
            self.assertEqual(self.client.post(
                f"/api/v1/agents/{uuid4()}/heartbeat").status_code, 503)
            self.assertEqual(self.client.post(
                f"/api/v1/agents/{uuid4()}/report",
                json={"status": "success", "packages": []}).status_code, 503)

    def test_symlinked_settings_rejected(self):
        target = Path(self.temp.name) / "target.json"
        self.settings.rename(target)
        self.settings.symlink_to(target)
        self.assert_both_disabled()

    def test_world_readable_settings_rejected(self):
        self.settings.chmod(0o644)
        self.assert_both_disabled()

    def test_group_writable_settings_rejected(self):
        self.settings.chmod(0o620)
        self.assert_both_disabled()

    def test_invalid_json_rejected(self):
        self.settings.write_text("{", encoding="utf-8")
        self.assert_both_disabled()

    def test_unexpected_setting_rejected(self):
        self.data["surprise"] = "value"
        self.write_settings()
        self.assert_both_disabled()

    def test_missing_setting_rejected(self):
        self.data.pop("tls_mode")
        self.write_settings()
        self.assert_both_disabled()

    def test_http_origin_rejected(self):
        self.data["public_url"] = "http://patch.example.test"
        self.write_settings()
        self.assert_both_disabled()

    def test_invalid_scan_interval_rejected(self):
        self.data["scan_interval_minutes"] = 0
        self.write_settings()
        self.assert_both_disabled()

    def test_malformed_feature_flag_rejected(self):
        self.data["reporting_enabled"] = "true"
        self.write_settings()
        self.assert_both_disabled()

    def test_missing_file_rejected(self):
        self.settings.unlink()
        self.assert_both_disabled()

    def test_unset_environment_gate_rejected(self):
        env = {**self.env, "ARBY_AGENT_REGISTRATION_ENABLED": "",
               "ARBY_AGENT_REPORTING_ENABLED": ""}
        self.assert_both_disabled(env)

    def test_runtime_gate_off_preserves_legacy_environment_behavior(self):
        with patch.dict(os.environ, {**self.env,
            "ARBY_SETTINGS_RUNTIME_ENABLED": "false"}, clear=True):
            flags = effective_flags()
            self.assertFalse(flags["registration_enabled"])
            self.assertFalse(flags["reporting_enabled"])
            # Existing legacy routes are deliberately unchanged without opt-in.
            from agent_feature_flags import registration_enabled, reporting_enabled
            self.assertTrue(registration_enabled())
            self.assertTrue(reporting_enabled())

    def test_valid_settings_only_allow_individually_enabled_features(self):
        with patch.dict(os.environ, {**self.env,
            "ARBY_AGENT_REPORTING_ENABLED": "false"}, clear=True):
            flags = effective_flags()
            self.assertTrue(flags["registration_enabled"])
            self.assertFalse(flags["reporting_enabled"])
            self.assertEqual(self.client.post(
                f"/api/v1/agents/{uuid4()}/heartbeat").status_code, 503)


if __name__ == "__main__":
    unittest.main()
