"""Workflow tests for the Versionary release provenance gate."""

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "installer/verify-release-provenance.py"

spec = importlib.util.spec_from_file_location(
    "versionary_provenance_workflow", SOURCE
)
provenance = importlib.util.module_from_spec(spec)
spec.loader.exec_module(provenance)


class WorkflowTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

        self.root = Path(self.temp.name)
        self.package = self.root / "versionary-agent.tar.gz"
        self.package.write_bytes(b"reproducible-package")

        self.commit = "a" * 40
        self.manifest = {
            "schema_version": 1,
            "product": "Versionary",
            "component": "agent",
            "version": "0.9.0-beta.1",
            "git_commit": self.commit,
            "package": {
                "filename": "versionary-agent.tar.gz",
                "sha256": provenance.sha256(self.package),
                "modules": 13,
            },
            "production_approved": False,
            "deployable": False,
        }

        self.manifest_path = self.root / "release-manifest.json"
        self.manifest_path.write_text(json.dumps(self.manifest))

        self.git_calls = []
        self.build_result = 0
        self.rebuilt_bytes = self.package.read_bytes()
        self.cleanup_fails = False
        self.release_valid = True

    def fake_git(self, *args, cwd=ROOT):
        self.git_calls.append(args)

        if args[:2] == ("rev-parse", "--verify"):
            return self.commit

        if args[:2] == ("rev-parse", "HEAD"):
            return self.commit

        if args[:2] == ("worktree", "remove") and self.cleanup_fails:
            raise provenance.ProvenanceError("simulated cleanup failure")

        return ""

    def fake_build(self, args, **kwargs):
        output = Path(args[args.index("--output") + 1])
        output.write_bytes(self.rebuilt_bytes)
        return subprocess.CompletedProcess(
            args, self.build_result, "", "simulated build failure"
        )

    def fake_release_module(self, checkout):
        class Release:
            def verify(inner_self, manifest, package):
                return self.release_valid

        return Release()

    def execute(self):
        with (
            patch.object(provenance, "git", side_effect=self.fake_git),
            patch.object(
                provenance.subprocess,
                "run",
                side_effect=self.fake_build,
            ),
            patch.object(
                provenance,
                "load_release_module",
                side_effect=self.fake_release_module,
            ),
        ):
            return provenance.verify(self.manifest_path, self.package)

    def test_successful_workflow(self):
        self.assertTrue(self.execute())
        self.assertTrue(
            any(call[:2] == ("worktree", "remove") for call in self.git_calls)
        )

    def test_reject_mismatched_checkout_commit(self):
        original = self.fake_git

        def mismatched(*args, **kwargs):
            if args[:2] == ("rev-parse", "HEAD"):
                return "b" * 40
            return original(*args, **kwargs)

        with patch.object(self, "fake_git", side_effect=mismatched):
            with self.assertRaisesRegex(
                provenance.ProvenanceError, "checkout commit mismatch"
            ):
                self.execute()

    def test_reject_failed_build(self):
        self.build_result = 1
        with self.assertRaisesRegex(
            provenance.ProvenanceError, "package build failed"
        ):
            self.execute()

    def test_reject_corrupted_rebuild(self):
        self.rebuilt_bytes = b"corrupted"
        with self.assertRaisesRegex(
            provenance.ProvenanceError, "checksum mismatch"
        ):
            self.execute()

    def test_reject_manifest_verification_failure(self):
        self.release_valid = False
        with self.assertRaisesRegex(
            provenance.ProvenanceError, "Manifest verification failed"
        ):
            self.execute()

    def test_cleanup_failure(self):
        self.cleanup_fails = True
        with self.assertRaisesRegex(
            provenance.ProvenanceError, "Worktree cleanup failed"
        ):
            self.execute()

    def test_combined_failure(self):
        self.cleanup_fails = True
        self.build_result = 1
        with self.assertRaisesRegex(
            provenance.ProvenanceError,
            "worktree cleanup also failed",
        ):
            self.execute()


if __name__ == "__main__":
    unittest.main()
