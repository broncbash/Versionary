"""Offline checks for opt-in signed release distribution endpoints."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from versionary_agent_distribution import router


class SignedDistributionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "versionary-agent.tar.gz").write_bytes(b"test-package")
        (self.root / "release-manifest.json").write_bytes(b"test-manifest")
        (self.root / "release-signature.json").write_bytes(b"test-signature")
        self.app = FastAPI()
        self.app.include_router(router)
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)

    def request(self, path, enabled=True):
        env = {
            "VERSIONARY_DISTRIBUTION_ENABLED": "true" if enabled else "false",
            "VERSIONARY_DISTRIBUTION_DIR": str(self.root),
        }
        with patch.dict(os.environ, env):
            return self.client.get("/api/v1/distribution/agent/" + path)

    def test_manifest_disabled(self):
        self.assertEqual(self.request("release-manifest", False).status_code, 404)

    def test_signature_disabled(self):
        self.assertEqual(self.request("release-signature", False).status_code, 404)

    def test_manifest_missing(self):
        (self.root / "release-manifest.json").unlink()
        self.assertEqual(self.request("release-manifest").status_code, 503)

    def test_signature_missing(self):
        (self.root / "release-signature.json").unlink()
        self.assertEqual(self.request("release-signature").status_code, 503)

    def test_manifest_served(self):
        content = b'{"test":"manifest"}'
        (self.root / "release-manifest.json").write_bytes(content)
        response = self.request("release-manifest")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, content)

    def test_signature_served(self):
        content = b'{"test":"signature"}'
        (self.root / "release-signature.json").write_bytes(content)
        response = self.request("release-signature")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, content)

    def test_manifest_symlink_rejected(self):
        target = self.root / "target"
        target.write_bytes(b"not trusted")
        (self.root / "release-manifest.json").unlink()
        (self.root / "release-manifest.json").symlink_to(target)
        self.assertEqual(self.request("release-manifest").status_code, 503)

    def test_signature_symlink_rejected(self):
        target = self.root / "target"
        target.write_bytes(b"not trusted")
        (self.root / "release-signature.json").unlink()
        (self.root / "release-signature.json").symlink_to(target)
        self.assertEqual(self.request("release-signature").status_code, 503)

    def test_world_writable_manifest_rejected(self):
        artifact = self.root / "release-manifest.json"
        artifact.write_bytes(b"test")
        artifact.chmod(0o666)
        self.assertEqual(self.request("release-manifest").status_code, 503)

    def test_empty_signature_rejected(self):
        (self.root / "release-signature.json").write_bytes(b"")
        self.assertEqual(self.request("release-signature").status_code, 503)


if __name__ == "__main__":
    unittest.main()
