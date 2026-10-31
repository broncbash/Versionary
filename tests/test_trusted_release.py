"""Tests for the unified Versionary trusted-release gate."""

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "installer/verify-trusted-release.py"

spec = importlib.util.spec_from_file_location(
    "versionary_trusted_release_tests", SOURCE
)
trusted = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trusted)


class TrustedReleaseTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

        root = Path(self.temp.name)
        self.manifest = root / "manifest.json"
        self.signature = root / "manifest.sig.json"
        self.public = root / "trusted-public.pem"
        self.package = root / "versionary-agent.tar.gz"

        self.manifest.write_text('{"product":"Versionary"}')
        self.signature.write_text("signature")
        self.public.write_text("public")
        self.package.write_bytes(b"package")

        self.signing = Mock()
        self.signing.verify.return_value = "sha256:" + "a" * 64

        self.provenance = Mock()
        self.provenance.verify.return_value = True

    def run_gate(self):
        def loader(name, module_name):
            if name == "release-signing.py":
                return self.signing
            if name == "verify-release-provenance.py":
                return self.provenance
            raise AssertionError("Unexpected module")

        with patch.object(trusted, "load_tool", side_effect=loader):
            return trusted.verify(
                self.manifest,
                self.signature,
                self.public,
                self.package,
            )

    def test_successful_combined_verification(self):
        self.assertTrue(self.run_gate())
        self.signing.verify.assert_called_once()
        self.provenance.verify.assert_called_once()

    def test_reject_untrusted_signature(self):
        self.signing.verify.side_effect = ValueError("untrusted key")

        with self.assertRaisesRegex(
            trusted.TrustedReleaseError,
            "Release authentication failed",
        ):
            self.run_gate()

        self.provenance.verify.assert_not_called()

    def test_reject_tampered_manifest(self):
        self.signing.verify.side_effect = ValueError(
            "Manifest checksum mismatch"
        )

        with self.assertRaises(trusted.TrustedReleaseError):
            self.run_gate()

        self.provenance.verify.assert_not_called()

    def test_reject_invalid_signature(self):
        self.signing.verify.side_effect = ValueError(
            "Ed25519 signature verification failed"
        )

        with self.assertRaises(trusted.TrustedReleaseError):
            self.run_gate()

        self.provenance.verify.assert_not_called()

    def test_reject_corrupted_package(self):
        self.provenance.verify.side_effect = ValueError(
            "Release package checksum mismatch"
        )

        with self.assertRaisesRegex(
            trusted.TrustedReleaseError,
            "Release provenance failed",
        ):
            self.run_gate()

    def test_reject_failed_rebuild(self):
        self.provenance.verify.side_effect = RuntimeError(
            "Isolated package build failed"
        )

        with self.assertRaises(trusted.TrustedReleaseError):
            self.run_gate()

    def test_reject_cleanup_failure(self):
        self.provenance.verify.side_effect = RuntimeError(
            "Worktree cleanup failed"
        )

        with self.assertRaises(trusted.TrustedReleaseError):
            self.run_gate()

    def test_authentication_precedes_provenance(self):
        calls = []

        self.signing.verify.side_effect = lambda *args: (
            calls.append("signature") or "sha256:" + "a" * 64
        )

        self.provenance.verify.side_effect = lambda *args: (
            calls.append("provenance") or True
        )

        self.assertTrue(self.run_gate())
        self.assertEqual(calls, ["signature", "provenance"])


if __name__ == "__main__":
    unittest.main()
