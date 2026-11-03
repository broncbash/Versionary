"""Offline security checks for the Versionary download-only preview."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "versionary_download_preview",
    ROOT / "installer/download-agent-preview.py",
)
download = importlib.util.module_from_spec(spec)
spec.loader.exec_module(download)


class DownloadPreviewTests(unittest.TestCase):
    def test_rejects_http(self):
        with self.assertRaises(download.DownloadError):
            download.validate_origin("http://example.org")

    def test_rejects_credentials(self):
        with self.assertRaises(download.DownloadError):
            download.validate_origin("https://user:pass@example.org")

    def test_rejects_paths(self):
        with self.assertRaises(download.DownloadError):
            download.validate_origin("https://example.org/path")

    def test_rejects_fragments(self):
        with self.assertRaises(download.DownloadError):
            download.validate_origin("https://example.org/#fragment")

    def test_rejects_invalid_port(self):
        with self.assertRaises(download.DownloadError):
            download.validate_origin("https://example.org:99999")

    def test_rejects_missing_trusted_key(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(download.DownloadError):
                download.preview(
                    "https://example.org",
                    Path(temp) / "missing.pem",
                )

    def test_rejects_symlink_trusted_key(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            original = base / "key.pem"
            original.write_text("placeholder")
            link = base / "link.pem"
            link.symlink_to(original)
            with self.assertRaises(download.DownloadError):
                download.preview("https://example.org", link)

    def test_tampered_signature_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            key = Ed25519PrivateKey.generate()
            public = base / "trusted.pem"
            public.write_bytes(
                key.public_key().public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo,
                )
            )
            manifest = base / "manifest.json"
            manifest.write_text('{"example":true}')
            signature = base / "signature.json"
            signing = download.load_tool(
                "release-signing.py", "versionary_download_test_signing"
            )
            envelope = {
                "schema_version": 1,
                "algorithm": "Ed25519",
                "key_id": signing.key_id(key.public_key()),
                "manifest_sha256": "0" * 64,
                "signature": "AAAA",
            }
            signature.write_text(json.dumps(envelope))
            package = base / "package.tar.gz"
            package.write_bytes(b"not an archive")
            with self.assertRaises(Exception):
                download.verify_files(
                    manifest, signature, package, public
                )

    def test_no_redirect_handler(self):
        handler = download.NoRedirect()
        with self.assertRaises(download.DownloadError):
            handler.redirect_request(
                None, None, 302, "Redirect", {}, "https://other.test"
            )


if __name__ == "__main__":
    unittest.main()
