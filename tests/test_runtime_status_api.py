"""Read-only runtime status endpoint regression tests."""
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from server_settings import DEFAULTS
from server_settings_api import router


class RuntimeStatusAPITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'settings.json'
        self.path.write_text(json.dumps({**DEFAULTS,
            'public_url': 'https://patch.example.test',
            'enrollment_enabled': True,
            'reporting_enabled': True}))
        self.path.chmod(0o600)
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)
        self.headers = {'Authorization': 'Bearer test-token'}
        self.env = {
            'ARBY_SETTINGS_PATH': str(self.path),
            'ARBY_ADMIN_TOKEN_HASH': hashlib.sha256(b'test-token').hexdigest(),
        }

    def test_authentication_required(self):
        with patch.dict(os.environ, self.env, clear=True):
            response = self.client.get('/api/v1/admin/settings/runtime-status')
            self.assertEqual(response.status_code, 401)

    def test_disabled_without_runtime_gates(self):
        with patch.dict(os.environ, self.env, clear=True):
            response = self.client.get('/api/v1/admin/settings/runtime-status', headers=self.headers)
            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.json()['applied'])
            self.assertFalse(response.json()['runtime']['registration_enabled'])
            self.assertFalse(response.json()['runtime']['reporting_enabled'])

    def test_reports_all_gates_without_applying(self):
        env = {**self.env, 'ARBY_SETTINGS_RUNTIME_ENABLED': 'true',
               'ARBY_AGENT_REGISTRATION_ENABLED': 'true',
               'ARBY_AGENT_REPORTING_ENABLED': 'true'}
        original = self.path.read_bytes()
        with patch.dict(os.environ, env, clear=True):
            response = self.client.get('/api/v1/admin/settings/runtime-status', headers=self.headers)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()['runtime']['configuration_valid'])
            self.assertTrue(response.json()['runtime']['registration_enabled'])
            self.assertTrue(response.json()['runtime']['reporting_enabled'])
            self.assertFalse(response.json()['applied'])
        self.assertEqual(self.path.read_bytes(), original)

    def test_corrupt_settings_fail_closed(self):
        self.path.write_text('{broken')
        with patch.dict(os.environ, {**self.env, 'ARBY_SETTINGS_RUNTIME_ENABLED': 'true'}, clear=True):
            response = self.client.get('/api/v1/admin/settings/runtime-status', headers=self.headers)
            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.json()['runtime']['configuration_valid'])
            self.assertFalse(response.json()['runtime']['registration_enabled'])
            self.assertFalse(response.json()['runtime']['reporting_enabled'])


if __name__ == '__main__':
    unittest.main()
