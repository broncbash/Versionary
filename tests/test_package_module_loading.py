"""Tests for loading validated agent modules from one archive snapshot."""

import importlib.util
import io
import tarfile
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "installer/validate-package.py"

spec = importlib.util.spec_from_file_location(
    "arby_package_validator", VALIDATOR
)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class TestPackageModuleLoading(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.archive = Path(self.temp.name) / "agent.tar.gz"

        self.modules = {
            name: f"# module: {name}\n".encode()
            for name in sorted(
                Path(name).name for name in validator.EXPECTED
            )
        }

    def write_archive(self, entries):
        with tarfile.open(self.archive, "w:gz") as archive:
            for name, data in entries:
                member = tarfile.TarInfo(name)
                member.size = len(data)
                archive.addfile(member, io.BytesIO(data))

    def valid_entries(self):
        return [
            (f"agent/{name}", data)
            for name, data in self.modules.items()
        ]

    def test_loads_exact_validated_bytes(self):
        self.write_archive(self.valid_entries())

        loaded = validator.load_modules(self.archive)

        self.assertEqual(loaded, self.modules)

    def test_rejects_duplicate_member(self):
        entries = self.valid_entries()
        entries.append(entries[0])
        self.write_archive(entries)

        with self.assertRaises(ValueError):
            validator.load_modules(self.archive)

    def test_rejects_unexpected_member(self):
        entries = self.valid_entries()
        entries.append(("agent/unexpected.py", b"unsafe\n"))
        self.write_archive(entries)

        with self.assertRaises(ValueError):
            validator.load_modules(self.archive)

    def test_rejects_missing_member(self):
        self.write_archive(self.valid_entries()[:-1])

        with self.assertRaises(ValueError):
            validator.load_modules(self.archive)

    def test_rejects_symlink_member(self):
        entries = self.valid_entries()

        with tarfile.open(self.archive, "w:gz") as archive:
            for index, (name, data) in enumerate(entries):
                member = tarfile.TarInfo(name)

                if index == 0:
                    member.type = tarfile.SYMTYPE
                    member.linkname = "identity.py"
                    archive.addfile(member)
                else:
                    member.size = len(data)
                    archive.addfile(member, io.BytesIO(data))

        with self.assertRaises(ValueError):
            validator.load_modules(self.archive)

    def test_rejects_oversized_member(self):
        entries = self.valid_entries()
        name, _ = entries[0]
        entries[0] = (
            name,
            b"x" * (validator.MAX_MODULE_SIZE + 1),
        )
        self.write_archive(entries)

        with self.assertRaises(ValueError):
            validator.load_modules(self.archive)


if __name__ == "__main__":
    unittest.main()
