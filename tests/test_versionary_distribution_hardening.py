"""Additional security checks for descriptor-based distribution."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from versionary_agent_distribution import router


class HardenedDistributionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

        self.package = self.root / "versionary-agent.tar.gz"
        self.manifest = self.root / "release-manifest.json"
        self.signature = self.root / "release-signature.json"

        self.package.write_bytes(b"package")
        self.manifest.write_bytes(b"manifest")
        self.signature.write_bytes(b"signature")

        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def get(self, endpoint):
        with patch.dict(os.environ, {
            "VERSIONARY_DISTRIBUTION_ENABLED": "true",
            "VERSIONARY_DISTRIBUTION_DIR": str(self.root),
        }):
            return self.client.get(
                "/api/v1/distribution/agent/" + endpoint
            )

    def test_package_delivered(self):
        response = self.get("package")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"package")

    def test_manifest_delivered(self):
        response = self.get("release-manifest")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"manifest")

    def test_signature_delivered(self):
        response = self.get("release-signature")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"signature")

    def test_symlink_directory_rejected(self):
        with tempfile.TemporaryDirectory() as other:
            link = Path(other) / "distribution"
            link.symlink_to(self.root, target_is_directory=True)
            with patch.dict(os.environ, {
                "VERSIONARY_DISTRIBUTION_ENABLED": "true",
                "VERSIONARY_DISTRIBUTION_DIR": str(link),
            }):
                response = self.client.get(
                    "/api/v1/distribution/agent/package"
                )
            self.assertEqual(response.status_code, 503)

    def test_package_symlink_rejected(self):
        self.package.unlink()
        self.package.symlink_to(self.manifest)
        self.assertEqual(self.get("package").status_code, 503)

    def test_missing_signature_blocks_signed_manifest(self):
        self.signature.unlink()
        self.assertEqual(
            self.get("release-manifest").status_code, 503
        )

    def test_missing_manifest_blocks_signed_signature(self):
        self.manifest.unlink()
        self.assertEqual(
            self.get("release-signature").status_code, 503
        )

    def test_world_writable_directory_rejected(self):
        original = self.root.stat().st_mode & 0o777
        try:
            self.root.chmod(0o777)
            self.assertEqual(self.get("package").status_code, 503)
        finally:
            self.root.chmod(original)

    def test_world_writable_signature_rejected(self):
        self.signature.chmod(0o666)
        self.assertEqual(
            self.get("release-signature").status_code, 503
        )


if __name__ == "__main__":
    unittest.main()
