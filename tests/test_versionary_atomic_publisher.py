"""Offline tests of Versionary's atomic publication component."""

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]


def load(filename, name):
    spec = importlib.util.spec_from_file_location(
        name, ROOT / "installer" / filename
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


publisher = load(
    "publish-agent-release.py",
    "versionary_atomic_publisher",
)
builder = load(
    "build-agent-package.py",
    "versionary_atomic_builder",
)
signing = load(
    "release-signing.py",
    "versionary_atomic_signing",
)


class AtomicPublisherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.destination = self.root / "published"
        self.destination.mkdir(mode=0o700)

        self.package = builder.build(
            self.root / "versionary-agent.tar.gz"
        )

        digest = hashlib.sha256(
            self.package.read_bytes()
        ).hexdigest()

        metadata = {
            "schema_version": 1,
            "product": "Versionary",
            "component": "agent",
            "version": "0.0.0-beta.1",
            "git_commit": "a" * 40,
            "package": {
                "filename": "versionary-agent.tar.gz",
                "sha256": digest,
                "modules": 13,
            },
            "production_approved": False,
            "deployable": False,
        }

        self.manifest = self.root / "release-manifest.json"
        self.manifest.write_text(json.dumps(metadata) + "\n")

        key = Ed25519PrivateKey.generate()

        self.private = self.root / "private.pem"
        self.public = self.root / "public.pem"
        self.signature = self.root / "release-signature.json"

        self.private.write_bytes(key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ))

        self.public.write_bytes(key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ))

        signing.sign(
            self.manifest,
            self.private,
            self.signature,
        )

    def publish(self):
        return publisher.publish(
            self.destination,
            self.package,
            self.manifest,
            self.signature,
            self.public,
        )

    def test_successful_atomic_publication(self):
        release_id = self.publish()
        active = self.destination / "current"
        self.assertTrue(active.is_symlink())
        self.assertEqual(
            active.readlink(),
            Path("releases") / release_id,
        )
        self.assertEqual(
            (active / "versionary-agent.tar.gz").read_bytes(),
            self.package.read_bytes(),
        )

    def test_duplicate_release_refused(self):
        self.publish()
        original = (self.destination / "current").readlink()
        with self.assertRaises(publisher.PublishError):
            self.publish()
        self.assertEqual(
            (self.destination / "current").readlink(),
            original,
        )

    def test_tampered_package_does_not_publish(self):
        self.package.write_bytes(
            self.package.read_bytes() + b"tampered"
        )
        with self.assertRaises(publisher.PublishError):
            self.publish()
        self.assertFalse(
            (self.destination / "current").exists()
        )

    def test_tampered_manifest_does_not_publish(self):
        self.manifest.write_bytes(
            self.manifest.read_bytes() + b" "
        )
        with self.assertRaises(Exception):
            self.publish()
        self.assertFalse(
            (self.destination / "current").exists()
        )

    def test_wrong_trusted_key_rejected(self):
        other = Ed25519PrivateKey.generate()
        self.public.write_bytes(
            other.public_key().public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )
        with self.assertRaises(Exception):
            self.publish()

    def test_symlink_input_rejected(self):
        link = self.root / "package-link.tar.gz"
        link.symlink_to(self.package)
        with self.assertRaises(OSError):
            publisher.publish(
                self.destination,
                link,
                self.manifest,
                self.signature,
                self.public,
            )

    def test_world_writable_root_rejected(self):
        self.destination.chmod(0o777)
        with self.assertRaises(publisher.PublishError):
            self.publish()

    def test_relative_destination_rejected(self):
        with self.assertRaises(publisher.PublishError):
            publisher.publish(
                Path("relative-path"),
                self.package,
                self.manifest,
                self.signature,
                self.public,
            )


if __name__ == "__main__":
    unittest.main()
