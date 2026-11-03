import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from versionary_agent_distribution import router


class DistributionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

        self.directory = Path(self.temp.name)
        self.package = self.directory / "versionary-agent.tar.gz"
        self.package.write_bytes(b"versionary-test-package")

        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def request(self, endpoint, enabled=True):
        values = {
            "VERSIONARY_DISTRIBUTION_ENABLED": (
                "true" if enabled else "false"
            ),
            "VERSIONARY_DISTRIBUTION_DIR": str(self.directory),
        }

        with patch.dict(os.environ, values):
            return self.client.get(
                "/api/v1/distribution/agent/" + endpoint
            )

    def test_disabled_by_default(self):
        self.assertEqual(
            self.request("manifest", enabled=False).status_code,
            404,
        )

    def test_manifest(self):
        response = self.request("manifest")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["sha256"],
            hashlib.sha256(self.package.read_bytes()).hexdigest(),
        )

    def test_download(self):
        response = self.request("package")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.content,
            b"versionary-test-package",
        )

    def test_missing_package(self):
        self.package.unlink()
        self.assertEqual(
            self.request("manifest").status_code,
            503,
        )

    def test_symlink_rejected(self):
        original = self.directory / "original.tar.gz"
        self.package.rename(original)
        self.package.symlink_to(original)

        self.assertEqual(
            self.request("package").status_code,
            503,
        )

    def test_world_writable_package_rejected(self):
        self.package.chmod(0o666)

        self.assertEqual(
            self.request("manifest").status_code,
            503,
        )

    def test_empty_package_rejected(self):
        self.package.write_bytes(b"")

        self.assertEqual(
            self.request("manifest").status_code,
            503,
        )


if __name__ == "__main__":
    unittest.main()
