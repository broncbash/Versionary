import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from server_settings import DEFAULTS, SettingsError, load, save
from server_settings_api import router
from fastapi import FastAPI

class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'settings.json'

    def test_defaults(self):
        self.assertEqual(load(self.path), DEFAULTS)

    def test_persistence(self):
        self.assertEqual(save({'public_url': 'https://10.1.2.3:8443'}, self.path)['public_url'], 'https://10.1.2.3:8443')
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

    def test_invalid_url(self):
        for url in ('http://host', 'https://user:pw@host', 'https://host/path', 'https://host:99999'):
            with self.subTest(url=url), self.assertRaises(SettingsError):
                save({'public_url': url}, self.path)

    def test_requires_public_url_for_activation(self):
        with self.assertRaises(SettingsError):
            save({'enrollment_enabled': True}, self.path)

    def test_no_unknown_keys(self):
        with self.assertRaises(SettingsError):
            save({'password': 'abc'}, self.path)

    def test_symlink_refused(self):
        target = Path(self.tmp.name) / 'target'
        target.write_text('keep')
        self.path.symlink_to(target)
        with self.assertRaises(SettingsError):
            save({'appearance': 'dark'}, self.path)
        self.assertEqual(target.read_text(), 'keep')

    def test_admin_auth(self):
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        with patch.dict(os.environ, {'ARBY_SETTINGS_PATH': str(self.path), 'ARBY_ADMIN_TOKEN_HASH': hashlib.sha256(b'test-token').hexdigest()}):
            self.assertEqual(client.get('/api/v1/admin/settings').status_code, 401)
            headers = {'Authorization': 'Bearer test-token'}
            self.assertEqual(client.get('/api/v1/admin/settings', headers=headers).status_code, 200)
            self.assertEqual(client.patch('/api/v1/admin/settings', headers=headers, json={'appearance': 'dark'}).status_code, 200)
            self.assertEqual(load(self.path)['appearance'], 'dark')
            self.assertEqual(client.patch('/api/v1/admin/settings', headers=headers, json={'unknown': 1}).status_code, 422)
            self.assertFalse(client.get('/api/v1/admin/settings', headers=headers).json()['applied'])
