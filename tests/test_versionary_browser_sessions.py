"""Isolated runtime security checks for Versionary beta sessions.

Run: .venv/bin/python -m unittest -v /path/to/test_versionary_browser_sessions.py
"""
import hashlib
import os
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
import versionary_browser_sessions as sessions
from admin_auth import require_admin
from fastapi import Depends

TOKEN = 'versionary-test-token-not-a-real-secret'
BASE = 'https://testserver'
ORIGIN = {'Origin': BASE}


class BrowserSessionSecurityTests(unittest.TestCase):
    def setUp(self):
        sessions._sessions.clear()
        self.env = patch.dict(os.environ, {
            'ARBY_ADMIN_TOKEN_HASH': hashlib.sha256(TOKEN.encode()).hexdigest()
        })
        self.env.start()
        app = FastAPI()
        app.include_router(sessions.router)
        @app.get('/bearer-only')
        def bearer_only(_=Depends(require_admin)):
            return {'ok': True}
        self.client = TestClient(app, base_url=BASE)

    def tearDown(self):
        self.client.close()
        sessions._sessions.clear()
        self.env.stop()

    def login(self):
        response = self.client.post('/admin/session/login', json={'token': TOKEN}, headers=ORIGIN)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()['csrf'], response

    def test_login_rejects_invalid_token_and_missing_origin(self):
        for headers, token, expected in ((ORIGIN, 'wrong', 401), ({}, TOKEN, 403)):
            r = self.client.post('/admin/session/login', json={'token': token}, headers=headers)
            self.assertEqual(r.status_code, expected, r.text)
        self.assertEqual(len(sessions._sessions), 0)

    def test_cookie_security_and_session_status(self):
        csrf, r = self.login()
        cookie = r.headers['set-cookie'].lower()
        for flag in ('secure', 'httponly', 'samesite=strict', 'path=/'):
            self.assertIn(flag, cookie)
        self.assertIn('__host-versionary-beta-session=', cookie)
        self.assertNotIn(TOKEN, cookie)
        status = self.client.get('/admin/session/status')
        self.assertEqual(status.status_code, 200)
        self.assertEqual(status.json()['csrf'], csrf)
        self.assertEqual(status.headers['cache-control'], 'no-store')

    def test_csrf_rejected_for_mutations(self):
        csrf, _ = self.login()
        agent = str(uuid4())
        with patch.object(sessions, 'approve_agent', return_value=True) as approve:
            for headers in ({}, {'X-Versionary-CSRF': csrf},
                            {'Origin': BASE, 'X-Versionary-CSRF': 'incorrect'}):
                r = self.client.post(f'/admin/session/agents/{agent}/approve', headers=headers)
                self.assertEqual(r.status_code, 403, r.text)
            approve.assert_not_called()
            r = self.client.post(f'/admin/session/agents/{agent}/approve',
                                 headers={**ORIGIN, 'X-Versionary-CSRF': csrf})
            self.assertEqual(r.status_code, 200, r.text)
            approve.assert_called_once_with(agent)

    def test_logout_revokes_cookie(self):
        csrf, _ = self.login()
        r = self.client.post('/admin/session/logout',
                             headers={**ORIGIN, 'X-Versionary-CSRF': csrf})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.client.get('/admin/session/status').status_code, 401)
        self.assertEqual(len(sessions._sessions), 0)

    def test_expiration(self):
        self.login()
        with patch.object(sessions.time, 'monotonic', return_value=float('inf')):
            self.assertEqual(self.client.get('/admin/session/status').status_code, 401)
        self.assertEqual(len(sessions._sessions), 0)

    def test_cookie_does_not_authorize_bearer_only_api(self):
        self.login()
        self.assertEqual(self.client.get('/bearer-only').status_code, 401)
        r = self.client.get('/bearer-only', headers={'Authorization': 'Bearer ' + TOKEN})
        self.assertEqual(r.status_code, 200, r.text)

    def test_dashboard_generation_and_headers(self):
        r = self.client.get('/admin/dashboard')
        self.assertEqual(r.status_code, 200, r.text[:200])
        self.assertIn('/admin/session/login', r.text)
        self.assertIn('/admin/session/logout', r.text)
        self.assertNotIn('sessionStorage', r.text)
        self.assertEqual(r.headers.get('cache-control'), 'no-store')
        self.assertIn('content-security-policy', r.headers)


if __name__ == '__main__':
    unittest.main()
