"""Regression tests for the read-only Settings UI runtime inspection surface."""
import unittest

from fastapi.testclient import TestClient

from main import app


class RuntimeStatusUITests(unittest.TestCase):
    def test_runtime_controls_are_present_and_accessible(self):
        with TestClient(app) as client:
            response = client.get('/admin/settings')
        self.assertEqual(response.status_code, 200)
        self.assertIn('id="runtime"', response.text)
        self.assertIn('id="runtime-result"', response.text)
        self.assertIn('aria-live="polite"', response.text)
        self.assertIn('/api/v1/admin/settings/runtime-status', response.text)
        self.assertIn('Read-only runtime status loaded.', response.text)
        self.assertIn('No changes applied.', response.text)

    def test_runtime_request_is_read_only_and_not_cached(self):
        with TestClient(app) as client:
            response = client.get('/admin/settings')
        self.assertIn("request('GET',undefined,'/api/v1/admin/settings/runtime-status')",
                      response.text)
        self.assertIn("cache:'no-store'", response.text)
        self.assertIn("credentials:'omit'", response.text)
        self.assertIn("body:data === undefined ? undefined", response.text)

    def test_runtime_endpoint_requires_admin(self):
        with TestClient(app) as client:
            response = client.get('/api/v1/admin/settings/runtime-status')
        self.assertEqual(response.status_code, 401)

    def test_ui_does_not_claim_runtime_configuration_applied(self):
        with TestClient(app) as client:
            response = client.get('/admin/settings')
        self.assertIn('STAGING MODE', response.text)
        self.assertIn('changes are saved but not applied', response.text)
        self.assertNotIn('localStorage', response.text)
        self.assertNotIn('sessionStorage', response.text)


if __name__ == '__main__':
    unittest.main()
