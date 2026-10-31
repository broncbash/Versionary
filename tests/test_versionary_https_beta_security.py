"""Runtime security tests for the isolated Versionary HTTPS beta."""

import importlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import versionary_https_beta as beta


class HTTPSBetaSecurityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

        self.root = Path(self.temp.name)
        self.state = self.root / "state"
        self.certs = self.state / "certs"

        self.state.mkdir(mode=0o700)
        self.certs.mkdir(mode=0o700)

        self.patch_state = patch.object(beta, "STATE", self.state)
        self.patch_certs = patch.object(beta, "CERTS", self.certs)
        self.patch_auth = patch.object(beta, "AUTH", self.state / "admin-token")

        for p in (self.patch_state, self.patch_certs, self.patch_auth):
            p.start()
            self.addCleanup(p.stop)

        for name in ("ca.key", "server.key", "ca.crt", "server.crt"):
            path = self.certs / name
            path.write_text("test fixture")
            path.chmod(0o600)

    def test_private_certificate_layout_accepted(self):
        beta.validate_certificates()

    def test_world_readable_server_key_rejected(self):
        (self.certs / "server.key").chmod(0o644)

        with self.assertRaises(RuntimeError):
            beta.validate_certificates()

    def test_world_readable_ca_key_rejected(self):
        (self.certs / "ca.key").chmod(0o644)

        with self.assertRaises(RuntimeError):
            beta.validate_certificates()

    def test_symlinked_server_key_rejected(self):
        key = self.certs / "server.key"
        key.unlink()
        key.symlink_to(self.certs / "ca.key")

        with self.assertRaises(RuntimeError):
            beta.validate_certificates()

    def test_symlinked_certificate_rejected(self):
        cert = self.certs / "server.crt"
        cert.unlink()
        cert.symlink_to(self.certs / "ca.crt")

        with self.assertRaises(RuntimeError):
            beta.validate_certificates()

    def test_world_accessible_cert_directory_rejected(self):
        self.certs.chmod(0o755)

        with self.assertRaises(RuntimeError):
            beta.validate_certificates()

    def test_symlinked_state_directory_rejected(self):
        other = self.root / "other"
        other.mkdir(mode=0o700)

        link = self.root / "linked-state"
        link.symlink_to(other, target_is_directory=True)

        with self.assertRaises(RuntimeError):
            beta.require_private_directory(link)

    def test_world_readable_admin_token_rejected(self):
        token = self.state / "admin-token"
        token.write_text("dummy-token")
        token.chmod(0o644)

        with self.assertRaises(RuntimeError):
            beta.prepare_state()

    def test_symlinked_admin_token_rejected(self):
        target = self.root / "target-token"
        target.write_text("dummy-token")
        target.chmod(0o600)

        (self.state / "admin-token").symlink_to(target)

        with self.assertRaises(RuntimeError):
            beta.prepare_state()


if __name__ == "__main__":
    unittest.main()
