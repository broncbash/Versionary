"""Regression tests for offline Versionary release signing."""

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "installer/release-signing.py"

spec = importlib.util.spec_from_file_location(
    "versionary_release_signing_tests", SOURCE
)
signing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(signing)


class ReleaseSigningTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

        root = Path(self.temp.name)
        self.private = root / "private.pem"
        self.public = root / "public.pem"
        self.manifest = root / "manifest.json"
        self.signature = root / "manifest.sig.json"

        self.manifest.write_text(
            '{"product":"Versionary","version":"0.9.0-beta.1"}\n'
        )

        self.identity = signing.keygen(self.private, self.public)

    def create_signature(self):
        signing.sign(
            self.manifest,
            self.private,
            self.signature,
        )

    def test_valid_signature(self):
        self.create_signature()
        self.assertEqual(
            signing.verify(
                self.manifest,
                self.signature,
                self.public,
            ),
            self.identity,
        )

    def test_private_key_permissions(self):
        self.assertEqual(
            os.stat(self.private).st_mode & 0o777,
            0o600,
        )

    def test_reject_manifest_tampering(self):
        self.create_signature()
        self.manifest.write_text(
            '{"product":"Versionary","version":"0.9.0-beta.2"}\n'
        )
        with self.assertRaises(signing.SigningError):
            signing.verify(
                self.manifest, self.signature, self.public
            )

    def test_reject_untrusted_key(self):
        self.create_signature()
        other_private = self.private.parent / "other-private.pem"
        other_public = self.public.parent / "other-public.pem"
        signing.keygen(other_private, other_public)

        with self.assertRaisesRegex(
            signing.SigningError, "not the trusted key"
        ):
            signing.verify(
                self.manifest, self.signature, other_public
            )

    def test_reject_corrupted_signature(self):
        self.create_signature()
        envelope = json.loads(self.signature.read_text())
        envelope["signature"] = "AAAA"
        self.signature.write_text(json.dumps(envelope))

        with self.assertRaises(signing.SigningError):
            signing.verify(
                self.manifest, self.signature, self.public
            )

    def test_reject_unknown_envelope_field(self):
        self.create_signature()
        envelope = json.loads(self.signature.read_text())
        envelope["bypass"] = True
        self.signature.write_text(json.dumps(envelope))

        with self.assertRaises(signing.SigningError):
            signing.verify(
                self.manifest, self.signature, self.public
            )

    def test_reject_overwrite_private_key(self):
        with self.assertRaises(signing.SigningError):
            signing.keygen(
                self.private,
                self.private.parent / "replacement.pem",
            )

    def test_reject_overwrite_signature(self):
        self.create_signature()
        with self.assertRaises(FileExistsError):
            self.create_signature()

    def test_reject_symlink_manifest(self):
        self.create_signature()
        link = self.manifest.parent / "manifest-link.json"
        link.symlink_to(self.manifest)

        with self.assertRaises(signing.SigningError):
            signing.verify(link, self.signature, self.public)

    def test_reject_invalid_key_identifier(self):
        self.create_signature()
        envelope = json.loads(self.signature.read_text())
        envelope["key_id"] = "../../unsafe"
        self.signature.write_text(json.dumps(envelope))

        with self.assertRaises(signing.SigningError):
            signing.verify(
                self.manifest, self.signature, self.public
            )


if __name__ == "__main__":
    unittest.main()
