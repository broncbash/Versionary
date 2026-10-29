"""Ownership security regression tests for CA installation."""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "installer/install-ca.py"
from test_agent_ca_installer import create_untrusted_ca
TRUSTED_CA = None

spec = importlib.util.spec_from_file_location(
    "arby_ca_ownership_tests", SCRIPT
)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class TestCAOwnershipSecurity(unittest.TestCase):

    def test_isolated_root_owned_by_invoker_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            ca = root / "test-ca.crt"
            ca.write_bytes(create_untrusted_ca())
            result = installer.install_ca(ca, root)

            self.assertEqual(
                result,
                installer.validate_ca(ca.read_bytes()),
            )

    def test_unsafe_root_permissions_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original_mode = root.stat().st_mode & 0o777

            try:
                root.chmod(0o777)

                with self.assertRaisesRegex(
                    ValueError, "permissions"
                ):
                    installer.install_ca(root / "missing.crt", root)

            finally:
                root.chmod(original_mode)

    def test_removed_test_override_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(TypeError):
                installer.install_ca(
                    TRUSTED_CA,
                    Path(tmp),
                    test_uid=os.geteuid(),
                )


if __name__ == "__main__":
    unittest.main()
