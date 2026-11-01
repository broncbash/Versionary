"""Beta 0.9 settings and certificate workflow contract tests."""
import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from server_settings import DEFAULTS, load
from server_settings_api import router as api_router
from settings_ui import router as page_router


class SettingsExperienceTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='versionary-settings-beta09-')
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / 'settings.json'
        app = FastAPI()
        app.include_router(page_router)
        app.include_router(api_router)
        self.client = TestClient(app)
        self.headers = {'Authorization': 'Bearer isolated-test-token'}
        self.environment = patch.dict(os.environ, {
            'ARBY_SETTINGS_PATH': str(self.path),
            'ARBY_ADMIN_TOKEN_HASH': hashlib.sha256(
                b'isolated-test-token').hexdigest(),
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def test_settings_page_has_versionary_branding(self):
        response = self.client.get('/admin/settings')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Versionary | Settings', response.text)
        self.assertNotIn('Patch Command | Settings', response.text)

    def test_certificate_mode_is_explicitly_staged(self):
        response = self.client.get('/admin/settings')
        self.assertIn('Planned TLS mode (not applied)', response.text)
        self.assertIn('No private key is uploaded through this page.', response.text)
        self.assertIn('installer/manage-certificates.py', response.text)
        self.assertIn('do not reload the proxy', response.text)

    def test_certificate_modes_are_saved_not_applied(self):
        for mode in ('external', 'local_ca', 'provided'):
            with self.subTest(mode=mode):
                response = self.client.patch(
                    '/api/v1/admin/settings',
                    headers=self.headers,
                    json={'tls_mode': mode},
                )
                self.assertEqual(response.status_code, 200)
                self.assertFalse(response.json()['applied'])
                self.assertEqual(load(self.path)['tls_mode'], mode)
                self.assertFalse(load(self.path)['enrollment_enabled'])
                self.assertFalse(load(self.path)['reporting_enabled'])

    def test_unauthenticated_cannot_read_or_change_settings(self):
        self.assertEqual(self.client.get('/api/v1/admin/settings').status_code, 401)
        self.assertEqual(self.client.patch('/api/v1/admin/settings',
                                           json={'tls_mode': 'provided'}).status_code, 401)
        self.assertEqual(load(self.path), DEFAULTS)

    def test_invalid_mode_does_not_change_saved_settings(self):
        response = self.client.patch('/api/v1/admin/settings',
                                     headers=self.headers,
                                     json={'tls_mode': 'auto-deploy'})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(load(self.path), DEFAULTS)

    def test_no_browser_token_persistence(self):
        html = self.client.get('/admin/settings').text
        for storage in ('localStorage', 'sessionStorage', 'document.cookie'):
            self.assertNotIn(storage, html)
        self.assertEqual(self.client.get('/admin/settings').headers['cache-control'], 'no-store')


if __name__ == '__main__':
    unittest.main()
