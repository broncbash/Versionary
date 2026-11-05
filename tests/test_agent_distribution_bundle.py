"""Offline tests for the Versionary agent distribution bundle."""
import importlib.util
import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "installer/build-agent-distribution.py"

spec = importlib.util.spec_from_file_location(
    "versionary_agent_distribution", SOURCE
)
distribution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(distribution)


class AgentDistributionTests(unittest.TestCase):

    def test_build_and_verify(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "distribution.tar.gz"
            distribution.build(output)
            metadata = distribution.verify(output)

            self.assertFalse(metadata["production_approved"])
            self.assertIn(
                "versionary_agent_cli.py",
                metadata["files"],
            )
            self.assertIn(
                "versionary-agent.tar.gz",
                metadata["files"],
            )

    def test_existing_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "distribution.tar.gz"
            output.write_bytes(b"preserve this file")

            with self.assertRaises(Exception):
                distribution.build(output)

            self.assertEqual(
                output.read_bytes(),
                b"preserve this file",
            )

    def test_reject_modified_cli(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = root / "original.tar.gz"
            modified = root / "modified.tar.gz"

            distribution.build(original)

            with tarfile.open(original, "r:gz") as archive:
                payload = {
                    member.name: archive.extractfile(member).read()
                    for member in archive.getmembers()
                }

            payload["versionary_agent_cli.py"] += b"\n# altered\n"

            with tarfile.open(modified, "w:gz") as archive:
                for name, data in payload.items():
                    info = tarfile.TarInfo(name)
                    info.size = len(data)
                    archive.addfile(info, io.BytesIO(data))

            with self.assertRaisesRegex(
                ValueError, "Checksum mismatch"
            ):
                distribution.verify(modified)

    def test_no_installation_side_effects(self):
        source = SOURCE.read_text()
        self.assertNotIn("systemctl ", source)
        self.assertNotIn("subprocess.run(", source)
        self.assertNotIn("apt install", source)
        self.assertNotIn("pacman -S", source)


if __name__ == "__main__":
    unittest.main()
