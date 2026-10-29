"""Security tests for the agent package validator."""

import importlib.util
import io
import tarfile
import tempfile
import unittest
from pathlib import Path


VALIDATOR = (
    Path(__file__).resolve().parents[1]
    / "installer/validate-package.py"
)

spec = importlib.util.spec_from_file_location(
    "agent_package_validator", VALIDATOR
)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class TestPackageValidator(unittest.TestCase):

    def make_archive(self, entries):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)

        path = Path(temp.name) / "agent.tar.gz"

        with tarfile.open(path, "w:gz") as archive:
            for name, data, kind in entries:
                info = tarfile.TarInfo(name)

                if kind == "file":
                    info.size = len(data)
                    archive.addfile(info, io.BytesIO(data))

                elif kind == "symlink":
                    info.type = tarfile.SYMTYPE
                    info.linkname = "/etc/passwd"
                    archive.addfile(info)

        return path

    def valid_entries(self):
        return [
            (name, b"# safe module\n", "file")
            for name in sorted(validator.EXPECTED)
        ]

    def test_valid_archive(self):
        path = self.make_archive(self.valid_entries())
        self.assertEqual(validator.validate(path), 13)

    def test_unexpected_file(self):
        entries = self.valid_entries()
        entries.append(("agent/extra.py", b"x", "file"))

        with self.assertRaises(ValueError):
            validator.validate(self.make_archive(entries))

    def test_path_traversal(self):
        entries = self.valid_entries()
        entries.append(("../escape.py", b"x", "file"))

        with self.assertRaises(ValueError):
            validator.validate(self.make_archive(entries))

    def test_symlink(self):
        entries = self.valid_entries()
        entries[0] = (
            entries[0][0], b"", "symlink"
        )

        with self.assertRaises(ValueError):
            validator.validate(self.make_archive(entries))

    def test_duplicate_entry(self):
        entries = self.valid_entries()
        entries.append(entries[0])

        with self.assertRaises(ValueError):
            validator.validate(self.make_archive(entries))

    def test_missing_module(self):
        entries = self.valid_entries()[:-1]

        with self.assertRaises(ValueError):
            validator.validate(self.make_archive(entries))

    def test_oversized_module(self):
        entries = self.valid_entries()
        entries[0] = (
            entries[0][0],
            b"x" * (validator.MAX_MODULE_SIZE + 1),
            "file",
        )

        with self.assertRaises(ValueError):
            validator.validate(self.make_archive(entries))


if __name__ == "__main__":
    unittest.main()
