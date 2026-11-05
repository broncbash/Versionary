"""Tests for Versionary's isolated release provenance gate."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "installer/verify-release-provenance.py"

spec = importlib.util.spec_from_file_location(
    "versionary_provenance_tests", SOURCE
)
provenance = importlib.util.module_from_spec(spec)
spec.loader.exec_module(provenance)


class ManifestValidationTests(unittest.TestCase):

    def setUp(self):
        self.manifest = {
            "schema_version": 1,
            "product": "Versionary",
            "component": "agent",
            "version": "0.9.0-beta.1",
            "git_commit": "a" * 40,
            "package": {
                "filename": "versionary-agent.tar.gz",
                "sha256": "b" * 64,
                "modules": 13,
            },
            "production_approved": False,
            "deployable": False,
        }

    def test_valid_manifest(self):
        self.assertEqual(
            provenance.validate_manifest(self.manifest),
            self.manifest,
        )

    def test_reject_modified_commit(self):
        self.manifest["git_commit"] = "../main"
        with self.assertRaises(provenance.ProvenanceError):
            provenance.validate_manifest(self.manifest)

    def test_reject_invalid_checksum(self):
        self.manifest["package"]["sha256"] = "not-a-checksum"
        with self.assertRaises(provenance.ProvenanceError):
            provenance.validate_manifest(self.manifest)

    def test_reject_production_approval(self):
        self.manifest["production_approved"] = True
        with self.assertRaises(provenance.ProvenanceError):
            provenance.validate_manifest(self.manifest)

    def test_reject_deployable_release(self):
        self.manifest["deployable"] = True
        with self.assertRaises(provenance.ProvenanceError):
            provenance.validate_manifest(self.manifest)

    def test_reject_extra_fields(self):
        self.manifest["unexpected"] = True
        with self.assertRaises(provenance.ProvenanceError):
            provenance.validate_manifest(self.manifest)

    def test_reject_boolean_module_count(self):
        self.manifest["package"]["modules"] = True
        with self.assertRaises(provenance.ProvenanceError):
            provenance.validate_manifest(self.manifest)

    def test_reject_invalid_version(self):
        self.manifest["version"] = "../../bad"
        with self.assertRaises(provenance.ProvenanceError):
            provenance.validate_manifest(self.manifest)

    def test_reject_invalid_filename(self):
        self.manifest["package"]["filename"] = "../agent.tar.gz"
        with self.assertRaises(provenance.ProvenanceError):
            provenance.validate_manifest(self.manifest)

    def test_reject_symlink_package(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            actual = root / "actual.tar.gz"
            actual.write_bytes(b"package")
            link = root / "versionary-agent.tar.gz"
            link.symlink_to(actual)

            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(self.manifest))

            with self.assertRaises(provenance.ProvenanceError):
                provenance.verify(manifest_path, link)

    def test_reject_package_tampering_before_git(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = root / "versionary-agent.tar.gz"
            package.write_bytes(b"tampered")
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(self.manifest))

            with patch.object(provenance, "git") as git_mock:
                with self.assertRaises(provenance.ProvenanceError):
                    provenance.verify(manifest_path, package)
                git_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
