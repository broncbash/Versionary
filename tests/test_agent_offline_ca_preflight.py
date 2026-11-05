"""Strict CA preflight regression tests for the offline installer."""

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.x509 import load_pem_x509_certificate


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "installer/install-agent-offline.py"

spec = importlib.util.spec_from_file_location(
    "versionary_offline_ca_preflight_tests",
    INSTALLER,
)
offline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(offline)


class OfflineCAPreflightTests(unittest.TestCase):

    def check_rejected_before_install(self, ca_contents, expected):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "isolated-root"
            root.mkdir(mode=0o700)

            ca = Path(temporary) / "ca.pem"
            ca.write_bytes(ca_contents)

            real_helper = offline.helper

            def select_helper(filename, name):
                if filename == "install-agent-cli.py":
                    return mock.Mock(
                        verified_cli=mock.Mock()
                    )
                return real_helper(filename, name)

            with (
                mock.patch.object(
                    offline,
                    "helper",
                    side_effect=select_helper,
                ),
                mock.patch.object(
                    offline,
                    "run_helper",
                ) as run_helper,
            ):
                with self.assertRaises(expected) as caught:
                    offline.install(
                        root,
                        Path(temporary) / "dummy-bundle.tar.gz",
                        "https://example.com:8766",
                        ca,
                    )

                self.assertTrue(
                    any(
                        marker in str(caught.exception).lower()
                        for marker in (
                            "certificate",
                            "private key",
                            "unable to load pem file",
                            "malformedframing",
                        )
                    ),
                    str(caught.exception),
                )
                run_helper.assert_not_called()

            self.assertEqual(list(root.iterdir()), [])

    def test_invalid_ca_rejected_before_install(self):
        self.check_rejected_before_install(
            b"not a certificate\n",
            ValueError,
        )

    def test_private_key_rejected_before_install(self):
        self.check_rejected_before_install(
            b"-----BEGIN PRIVATE KEY-----\n"
            b"forbidden\n"
            b"-----END PRIVATE KEY-----\n",
            ValueError,
        )


if __name__ == "__main__":
    unittest.main()
