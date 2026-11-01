import unittest
from fastapi.testclient import TestClient
from main import app

class SettingsUITests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_page_served(self):
        response = self.client.get('/admin/settings')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Versionary | Settings', response.text)
        self.assertIn('STAGING MODE', response.text)

    def test_no_cache_and_frame_protection(self):
        response = self.client.get('/admin/settings')
        self.assertEqual(response.headers['cache-control'], 'no-store')
        self.assertEqual(response.headers['x-frame-options'], 'DENY')
        self.assertIn("default-src 'none'", response.headers['content-security-policy'])

    def test_api_still_requires_auth(self):
        response = self.client.get('/api/v1/admin/settings')
        self.assertEqual(response.status_code, 401)

    def test_page_does_not_persist_token(self):
        response = self.client.get('/admin/settings')
        self.assertNotIn('localStorage', response.text)
        self.assertNotIn('sessionStorage', response.text)
        self.assertNotIn('document.cookie', response.text)

if __name__ == '__main__':
    unittest.main()
