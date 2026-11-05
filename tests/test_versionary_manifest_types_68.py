"""Fail-closed validation of isolated upgrade manifest JSON."""

import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "installer"


def load(filename, name):
    spec = importlib.util.spec_from_file_location(
        name, INSTALLER / filename
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


coordinator = load(
    "versionary-agent-isolated-coordinator.py",
    "versionary_manifest68_coordinator",
)
upgrade = load(
    "versionary-agent-isolated-upgrade.py",
    "versionary_manifest68_upgrade",
)


class ManifestTypeTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="versionary-manifest68-"
        )
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

        self.old = {
            name: f"old:{name}".encode()
            for name in coordinator.MODES
        }
        self.new = {
            name: f"new:{name}".encode()
            for name in coordinator.MODES
        }

        coordinator.install_payloads_isolated(
            self.root, self.old
        )
        upgrade.apply(self.root, self.old, self.new)

        self.manifest = (
            self.root
            / ".versionary-upgrade-transaction"
            / "manifest.json"
        )

    def test_invalid_manifest_types_fail_closed(self):
        invalid = (
            b"null",
            b"[]",
            b'"string"',
            b"42",
            b"true",
            b"{broken",
            b"\xff",
        )

        for content in invalid:
            with self.subTest(content=content):
                self.manifest.write_bytes(content)

                with self.assertRaises(ValueError):
                    upgrade.recover_to_old(self.root)

                for name, expected in self.new.items():
                    self.assertEqual(
                        (self.root / name).read_bytes(),
                        expected,
                    )

    def test_valid_manifest_recovery_unchanged(self):
        result = upgrade.recover_to_old(self.root)

        self.assertEqual(
            result["restored"],
            len(self.old),
        )

        for name, expected in self.old.items():
            self.assertEqual(
                (self.root / name).read_bytes(),
                expected,
            )


if __name__ == "__main__":
    unittest.main()
