"""Content-aware system installation conflict tests."""

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "installer/versionary-agent-system-content.py"

spec = importlib.util.spec_from_file_location(
    "versionary_system_content",
    SOURCE,
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SystemContentTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

        self.payloads = {
            "etc/versionary-agent/config.json": b"expected\n",
            "etc/versionary-agent/ca.crt": b"certificate\n",
        }

    def test_absent_files_accepted(self):
        result = module.inspect_existing(
            self.root, self.payloads
        )

        self.assertEqual(
            set(result.values()),
            {"absent"},
        )

    def test_identical_existing_file_accepted(self):
        target = self.root / "etc/versionary-agent/config.json"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"expected\n")
        target.chmod(0o644)

        result = module.inspect_existing(
            self.root, self.payloads
        )

        self.assertEqual(
            result["etc/versionary-agent/config.json"],
            "identical",
        )

    def test_different_existing_file_rejected(self):
        target = self.root / "etc/versionary-agent/config.json"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"different\n")

        with self.assertRaisesRegex(
            ValueError,
            "differs",
        ):
            module.inspect_existing(
                self.root, self.payloads
            )

    def test_symlinked_existing_file_rejected(self):
        target = self.root / "etc/versionary-agent/config.json"
        target.parent.mkdir(parents=True)
        target.symlink_to(self.root)

        with self.assertRaises(ValueError):
            module.inspect_existing(
                self.root, self.payloads
            )

    def test_hardlinked_existing_file_rejected(self):
        target = self.root / "etc/versionary-agent/config.json"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"expected\n")
        (target.parent / "other").hardlink_to(target)

        with self.assertRaises(ValueError):
            module.inspect_existing(
                self.root, self.payloads
            )

    def test_world_writable_existing_file_rejected(self):
        target = self.root / "etc/versionary-agent/config.json"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"expected\n")
        target.chmod(0o666)

        with self.assertRaises(ValueError):
            module.inspect_existing(
                self.root, self.payloads
            )

    def test_no_files_modified(self):
        target = self.root / "etc/versionary-agent/config.json"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"expected\n")

        before = target.read_bytes()

        module.inspect_existing(
            self.root, self.payloads
        )

        self.assertEqual(target.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
