"""CLI/API parity for read-only runtime gate inspection."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from server_settings import DEFAULTS
from server_settings_api import router

ROOT = Path(__file__).resolve().parents[1]


class RuntimeStatusParityTests(unittest.TestCase):
    def test_cli_matches_admin_api_without_mutation(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'settings.json'
            path.write_text(json.dumps({**DEFAULTS,
                'public_url': 'https://patch.example.test',
                'enrollment_enabled': True,
                'reporting_enabled': False}))
            path.chmod(0o600)
            before = path.read_bytes()
            env = {
                'ARBY_SETTINGS_PATH': str(path),
                'ARBY_SETTINGS_RUNTIME_ENABLED': 'true',
                'ARBY_AGENT_REGISTRATION_ENABLED': 'true',
                'ARBY_AGENT_REPORTING_ENABLED': 'true',
                'ARBY_ADMIN_TOKEN_HASH': hashlib.sha256(b'test-token').hexdigest(),
            }
            with patch.dict(os.environ, env, clear=True):
                api = FastAPI()
                api.include_router(router)
                response = TestClient(api).get(
                    '/api/v1/admin/settings/runtime-status',
                    headers={'Authorization': 'Bearer test-token'})
                self.assertEqual(response.status_code, 200)
                proc = subprocess.run(
                    [sys.executable, str(ROOT / 'installer/settings-cli.py'),
                     '--path', str(path), 'runtime-status'],
                    env=os.environ.copy(), capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(proc.stdout), response.json())
            self.assertEqual(path.read_bytes(), before)

    def test_cli_missing_settings_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'missing.json'
            env = {**os.environ,
                'ARBY_SETTINGS_RUNTIME_ENABLED': 'true',
                'ARBY_AGENT_REGISTRATION_ENABLED': 'true'}
            proc = subprocess.run(
                [sys.executable, str(ROOT / 'installer/settings-cli.py'),
                 '--path', str(path), 'runtime-status'],
                env=env, capture_output=True, text=True, check=True)
            result = json.loads(proc.stdout)['runtime']
            self.assertFalse(result['registration_enabled'])
            self.assertFalse(result['configuration_valid'])
            self.assertFalse(path.exists())


if __name__ == '__main__':
    unittest.main()
