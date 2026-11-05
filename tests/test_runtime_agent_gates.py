"""Integration tests for optional settings-gated legacy agent routes.

No production service is modified; v2 routes remain isolated.
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
from agent_feature_flags import registration_enabled, reporting_enabled
from server_settings import DEFAULTS


class RuntimeAgentGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'settings.json'
        self.path.write_text(json.dumps({**DEFAULTS, 'public_url': 'https://patch.example.test',
            'enrollment_enabled': True, 'reporting_enabled': True}))
        self.path.chmod(0o600)
        self.env = {'ARBY_SETTINGS_PATH': str(self.path),
            'ARBY_SETTINGS_RUNTIME_ENABLED': 'true',
            'ARBY_AGENT_REGISTRATION_ENABLED': 'true',
            'ARBY_AGENT_REPORTING_ENABLED': 'true'}
        app = FastAPI()
        app.include_router(registration_router)
        app.include_router(reporting_router)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_valid_configuration_allows_existing_flags(self):
        with patch.dict(os.environ, self.env, clear=True):
            self.assertTrue(registration_enabled())
            self.assertTrue(reporting_enabled())

    def test_missing_settings_disables_both(self):
        with patch.dict(os.environ, {**self.env,
            'ARBY_SETTINGS_PATH': str(self.path.parent / 'missing.json')}, clear=True):
            self.assertFalse(registration_enabled())
            self.assertFalse(reporting_enabled())
            self.assertEqual(self.client.post('/api/v1/agents/register',
                json={'agent_id': str(uuid4()), 'hostname': 'test', 'platform': 'arch'}).status_code, 503)
            self.assertEqual(self.client.post(f'/api/v1/agents/{uuid4()}/heartbeat').status_code, 503)

    def test_invalid_settings_disables_both(self):
        self.path.write_text('{bad')
        with patch.dict(os.environ, self.env, clear=True):
            self.assertFalse(registration_enabled())
            self.assertFalse(reporting_enabled())

    def test_settings_cannot_override_environment(self):
        with patch.dict(os.environ, {**self.env,
            'ARBY_AGENT_REGISTRATION_ENABLED': 'false',
            'ARBY_AGENT_REPORTING_ENABLED': 'false'}, clear=True):
            self.assertFalse(registration_enabled())
            self.assertFalse(reporting_enabled())

    def test_settings_disable_features_independently(self):
        self.path.write_text(json.dumps({**DEFAULTS,
            'public_url': 'https://patch.example.test',
            'enrollment_enabled': False, 'reporting_enabled': True}))
        with patch.dict(os.environ, self.env, clear=True):
            self.assertFalse(registration_enabled())
            self.assertTrue(reporting_enabled())

    def test_legacy_behavior_preserved_without_opt_in(self):
        with patch.dict(os.environ, {'ARBY_SETTINGS_PATH': str(self.path.parent / 'missing.json'),
            'ARBY_AGENT_REGISTRATION_ENABLED': 'true',
            'ARBY_AGENT_REPORTING_ENABLED': 'true'}, clear=True):
            self.assertTrue(registration_enabled())
            self.assertTrue(reporting_enabled())

    def test_status_endpoint_matches_effective_gates(self):
        with patch.dict(os.environ, {**self.env,
            'ARBY_AGENT_REPORTING_ENABLED': 'false'}, clear=True):
            response = self.client.get('/api/v1/agents/status')
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()['registration_enabled'])
            self.assertFalse(response.json()['reporting_enabled'])


if __name__ == '__main__':
    unittest.main()
