"""Isolated recovery journal tests."""

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "installer/versionary-agent-system-journal.py"

spec = importlib.util.spec_from_file_location(
    "versionary_system_journal",
    SOURCE,
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class JournalTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.payloads = {
            "etc/versionary-agent/config.json": b"config",
            "etc/versionary-agent/ca.crt": b"certificate",
        }

    def test_journal_records_hashes_and_sizes(self):
        journal = module.make_journal(self.payloads)

        entry = journal["files"][
            "etc/versionary-agent/config.json"
        ]

        self.assertEqual(entry["size"], 6)
        self.assertEqual(entry["sha256"], module.digest(b"config"))

    def test_journal_round_trip(self):
        journal = module.make_journal(self.payloads)
        module.write_journal(self.root, journal)

        loaded = module.read_journal(self.root)
        self.assertEqual(loaded, journal)

    def test_refuses_overwrite_existing_journal(self):
        journal = module.make_journal(self.payloads)
        module.write_journal(self.root, journal)

        with self.assertRaises(FileExistsError):
            module.write_journal(self.root, journal)

    def test_recovery_reports_absent_files(self):
        journal = module.make_journal(self.payloads)

        result = module.inspect_recovery(self.root, journal)

        self.assertEqual(set(result.values()), {"absent"})

    def test_recovery_accepts_matching_files(self):
        journal = module.make_journal(self.payloads)

        target = self.root / "etc/versionary-agent/config.json"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"config")

        result = module.inspect_recovery(self.root, journal)

        self.assertEqual(
            result["etc/versionary-agent/config.json"],
            "matches",
        )

    def test_recovery_rejects_modified_file(self):
        journal = module.make_journal(self.payloads)

        target = self.root / "etc/versionary-agent/config.json"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"changed")

        with self.assertRaises(module.JournalConflict):
            module.inspect_recovery(self.root, journal)

    def test_recovery_rejects_symlink(self):
        journal = module.make_journal(self.payloads)

        target = self.root / "etc/versionary-agent/config.json"
        target.parent.mkdir(parents=True)
        target.symlink_to(self.root)

        with self.assertRaises(module.JournalConflict):
            module.inspect_recovery(self.root, journal)

    def test_rejects_traversal_in_journal(self):
        with self.assertRaises(ValueError):
            module.make_journal({"../outside": b"unsafe"})

    def test_refuses_system_root(self):
        journal = module.make_journal(self.payloads)

        with self.assertRaises(ValueError):
            module.write_journal(Path("/"), journal)


if __name__ == "__main__":
    unittest.main()
