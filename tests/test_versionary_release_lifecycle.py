"""Disposable filesystem tests for release activation and rollback."""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lifecycle = load(
    ROOT / "installer" / "release-lifecycle.py",
    "versionary_test_lifecycle",
)

existing = load(
    ROOT / "tests" / "test_versionary_atomic_publisher.py",
    "versionary_existing_atomic_tests",
)


class ReleaseLifecycleTests(
    existing.AtomicPublisherTests
):
    """Reuse the real signed-release fixture."""

    def test_verified_release_activation(self):
        release_id = self.publish()

        metadata = lifecycle.verify_release(
            self.destination,
            release_id,
            self.public,
        )

        self.assertEqual(
            metadata["version"],
            "0.0.0-beta.1",
        )

        self.assertEqual(
            lifecycle.active_release(self.destination),
            release_id,
        )

    def test_reactivation_is_idempotent(self):
        release_id = self.publish()

        previous = lifecycle.activate(
            self.destination,
            release_id,
            self.public,
        )

        self.assertEqual(previous, release_id)
        self.assertEqual(
            lifecycle.active_release(self.destination),
            release_id,
        )

    def test_invalid_release_id_rejected(self):
        self.publish()

        for invalid in (
            "../outside",
            "a" * 63,
            "A" * 64,
            "a" * 64 + "/other",
            "",
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaises(
                    lifecycle.LifecycleError
                ):
                    lifecycle.verify_release(
                        self.destination,
                        invalid,
                        self.public,
                    )

    def test_tampered_stored_release_rejected(self):
        release_id = self.publish()
        package = (
            self.destination
            / "releases"
            / release_id
            / "versionary-agent.tar.gz"
        )

        package.chmod(0o600)
        package.write_bytes(
            package.read_bytes() + b"tampered"
        )

        with self.assertRaises(Exception):
            lifecycle.verify_release(
                self.destination,
                release_id,
                self.public,
            )

        self.assertEqual(
            lifecycle.active_release(self.destination),
            release_id,
        )

    def test_wrong_key_prevents_activation(self):
        release_id = self.publish()

        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey,
        )

        other = Ed25519PrivateKey.generate()
        wrong = self.root / "wrong.pem"
        wrong.write_bytes(
            other.public_key().public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )

        with self.assertRaises(Exception):
            lifecycle.activate(
                self.destination,
                release_id,
                wrong,
            )

        self.assertEqual(
            lifecycle.active_release(self.destination),
            release_id,
        )

    def test_pointer_replace_failure_preserves_active(self):
        release_id = self.publish()

        pointer = self.destination / "current"
        before = os.readlink(pointer)

        pointer.unlink()

        real_replace = os.replace

        def fail_replace(source, target):
            if Path(target) == pointer:
                raise OSError("Simulated pointer switch failure")
            return real_replace(source, target)

        with patch.object(
            lifecycle.os,
            "replace",
            side_effect=fail_replace,
        ):
            with self.assertRaises(OSError):
                lifecycle.activate(
                    self.destination,
                    release_id,
                    self.public,
                )

        self.assertFalse(pointer.exists())
        self.assertFalse(
            (self.destination / (
                ".activate-" + release_id[:16]
            )).is_symlink()
        )

        pointer.symlink_to(before)

    def test_unsafe_pointer_rejected(self):
        release_id = self.publish()

        pointer = self.destination / "current"
        pointer.unlink()
        pointer.symlink_to("../../outside")

        with self.assertRaises(
            lifecycle.LifecycleError
        ):
            lifecycle.active_release(self.destination)

        with self.assertRaises(
            lifecycle.LifecycleError
        ):
            lifecycle.activate(
                self.destination,
                release_id,
                self.public,
            )

    def test_symlink_release_directory_rejected(self):
        release_id = self.publish()
        releases = self.destination / "releases"

        link = releases / ("b" * 64)
        link.symlink_to(releases / release_id)

        with self.assertRaises(
            lifecycle.LifecycleError
        ):
            lifecycle.verify_release(
                self.destination,
                "b" * 64,
                self.public,
            )


if __name__ == "__main__":
    unittest.main()
