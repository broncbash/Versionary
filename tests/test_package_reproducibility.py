"""Regression tests for deterministic Versionary agent packages."""

import gzip
import hashlib
import importlib.util
import struct
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "installer/build-agent-package.py"

spec = importlib.util.spec_from_file_location(
    "versionary_reproducible_package_builder", BUILDER
)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class PackageReproducibilityTests(unittest.TestCase):

    def test_independent_builds_are_byte_identical(self):
        with tempfile.TemporaryDirectory(
            prefix="versionary-reproducibility-"
        ) as directory:
            root = Path(directory)
            first = root / "first.tar.gz"
            second = root / "second.tar.gz"

            builder.build(first)
            builder.build(second)

            first_bytes = first.read_bytes()
            second_bytes = second.read_bytes()

            self.assertEqual(
                hashlib.sha256(first_bytes).digest(),
                hashlib.sha256(second_bytes).digest()
            )
            self.assertEqual(first_bytes, second_bytes)

            self.assertEqual(
                gzip.decompress(first_bytes),
                gzip.decompress(second_bytes)
            )

    def test_gzip_header_contains_no_timestamp_or_filename(self):
        with tempfile.TemporaryDirectory(
            prefix="versionary-gzip-header-"
        ) as directory:
            archive = Path(directory) / "named-output.tar.gz"
            builder.build(archive)

            data = archive.read_bytes()

            self.assertEqual(data[:3], b"\x1f\x8b\x08")
            self.assertEqual(struct.unpack("<I", data[4:8])[0], 0)
            self.assertEqual(data[3] & 0x08, 0)


if __name__ == "__main__":
    unittest.main()
