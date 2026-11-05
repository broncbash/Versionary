"""Versionary release manifest verification tests."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "installer/release-metadata.py"

spec = importlib.util.spec_from_file_location(
    "versionary_release_metadata", SOURCE
)
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseMetadataTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.package = Path(self.temp.name) / "versionary-agent.tar.gz"
        self.package.write_bytes(b"test-package")

        self.identity = patch.object(
            release, "committed_identity", return_value="a" * 40
        )
        self.modules = patch.object(
            release, "package_modules", return_value=13
        )

        self.identity.start()
        self.modules.start()

        self.addCleanup(self.identity.stop)
        self.addCleanup(self.modules.stop)

    def test_canonical_version(self):
        self.assertEqual(release.release_version(), "0.9.0-beta.1")

    def test_generate_and_verify(self):
        manifest = release.generate(self.package)
        self.assertTrue(release.verify(manifest, self.package))
        self.assertEqual(manifest["package"]["modules"], 13)
        self.assertFalse(manifest["deployable"])

    def test_reject_modified_package(self):
        manifest = release.generate(self.package)
        self.package.write_bytes(b"tampered")
        with self.assertRaises(ValueError):
            release.verify(manifest, self.package)

    def test_reject_production_approval(self):
        manifest = release.generate(self.package)
        manifest["production_approved"] = True
        with self.assertRaises(ValueError):
            release.verify(manifest, self.package)

    def test_reject_deployable_manifest(self):
        manifest = release.generate(self.package)
        manifest["deployable"] = True
        with self.assertRaises(ValueError):
            release.verify(manifest, self.package)

    def test_reject_modified_commit(self):
        manifest = release.generate(self.package)
        manifest["git_commit"] = "b" * 40
        with self.assertRaises(ValueError):
            release.verify(manifest, self.package)

    def test_reject_unexpected_field(self):
        manifest = release.generate(self.package)
        manifest["secret"] = "unexpected"
        with self.assertRaises(ValueError):
            release.verify(manifest, self.package)

    def test_reject_boolean_schema_version(self):
        manifest = release.generate(self.package)
        manifest["schema_version"] = True
        with self.assertRaises(ValueError):
            release.verify(manifest, self.package)


if __name__ == "__main__":
    unittest.main()
