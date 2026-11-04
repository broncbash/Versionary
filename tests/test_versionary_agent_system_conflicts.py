"""System beta destination conflict tests."""

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "installer/versionary-agent-system-conflicts.py"

spec = importlib.util.spec_from_file_location(
    "versionary_system_conflicts",
    SOURCE,
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SystemConflictTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_empty_root_accepted(self):
        result = module.inspect(self.root)
        self.assertEqual(
            result["files"][
                "etc/versionary-agent/config.json"
            ],
            "absent",
        )

    def test_symlinked_directory_rejected(self):
        (self.root / "opt").symlink_to(self.root)

        with self.assertRaises(ValueError):
            module.inspect(self.root)

    def test_world_writable_directory_rejected(self):
        target = self.root / "opt"
        target.mkdir()
        target.chmod(0o777)

        with self.assertRaises(ValueError):
            module.inspect(self.root)

    def test_private_state_requires_0700(self):
        target = self.root / "var/lib/versionary-agent"
        target.mkdir(parents=True)
        target.chmod(0o755)

        with self.assertRaises(ValueError):
            module.inspect(self.root)

    def test_symlinked_config_rejected(self):
        target = self.root / "etc/versionary-agent"
        target.mkdir(parents=True)
        (target / "config.json").symlink_to(self.root)

        with self.assertRaises(ValueError):
            module.inspect(self.root)

    def test_existing_regular_file_accepted(self):
        target = self.root / "etc/versionary-agent"
        target.mkdir(parents=True)
        config = target / "config.json"
        config.write_text("{}")
        config.chmod(0o644)

        result = module.inspect(self.root)

        self.assertEqual(
            result["files"][
                "etc/versionary-agent/config.json"
            ],
            "existing",
        )

    def test_hardlinked_config_rejected(self):
        target = self.root / "etc/versionary-agent"
        target.mkdir(parents=True)
        config = target / "config.json"
        config.write_text("{}")
        (target / "other").hardlink_to(config)

        with self.assertRaises(ValueError):
            module.inspect(self.root)

    def test_no_files_created(self):
        before = set(self.root.rglob("*"))
        module.inspect(self.root)
        after = set(self.root.rglob("*"))

        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
