import hashlib
import os
import unittest

from unittest.mock import patch

from admin_auth import authenticate_admin
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from admin_auth import require_admin


class TestAdminAuth(unittest.TestCase):

    def setUp(self):
        self.token = "test-admin-token-only"
        self.token_hash = hashlib.sha256(
            self.token.encode("utf-8")
        ).hexdigest()

    def test_valid_admin_token(self):
        with patch.dict(
            os.environ,
            {"ARBY_ADMIN_TOKEN_HASH": self.token_hash},
        ):
            self.assertTrue(authenticate_admin(self.token))

    def test_invalid_admin_token(self):
        with patch.dict(
            os.environ,
            {"ARBY_ADMIN_TOKEN_HASH": self.token_hash},
        ):
            self.assertFalse(
                authenticate_admin("incorrect-token")
            )

    def test_missing_admin_token(self):
        with patch.dict(
            os.environ,
            {"ARBY_ADMIN_TOKEN_HASH": self.token_hash},
        ):
            self.assertFalse(authenticate_admin(None))

    def test_unconfigured_admin_authentication(self):
        with patch.dict(os.environ):
            os.environ.pop("ARBY_ADMIN_TOKEN_HASH", None)
            self.assertFalse(authenticate_admin(self.token))

    def test_malformed_admin_hash(self):
        with patch.dict(
            os.environ,
            {"ARBY_ADMIN_TOKEN_HASH": "invalid-hash"},
        ):
            self.assertFalse(authenticate_admin(self.token))

    def test_protected_endpoint_requires_valid_token(self):
        app = FastAPI()

        @app.get("/admin-test")
        def protected_endpoint(_: None = Depends(require_admin)):
            return {"status": "authorized"}

        with patch.dict(
            os.environ,
            {"ARBY_ADMIN_TOKEN_HASH": self.token_hash},
        ):
            with TestClient(app) as client:
                missing = client.get("/admin-test")

                invalid = client.get(
                    "/admin-test",
                    headers={
                        "Authorization": "Bearer wrong-token"
                    },
                )

                valid = client.get(
                    "/admin-test",
                    headers={
                        "Authorization": f"Bearer {self.token}"
                    },
                )

        self.assertEqual(missing.status_code, 401)
        self.assertEqual(invalid.status_code, 401)
        self.assertEqual(valid.status_code, 200)
        self.assertEqual(
            valid.json(),
            {"status": "authorized"},
        )
