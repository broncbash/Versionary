"""Tests for the opt-in disposable desktop agent lab."""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "installer/try-agent-lab.py"
spec = importlib.util.spec_from_file_location("try_agent_lab", SOURCE)
lab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab)


class AgentLabTests(unittest.TestCase):
    def test_private_empty_workspace_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(lab.workspace_guard(directory), Path(directory))

    def test_nonempty_workspace_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "existing").write_text("preserve")
            with self.assertRaises(ValueError):
                lab.workspace_guard(directory)
            self.assertEqual((Path(directory) / "existing").read_text(), "preserve")

    def test_root_refused(self):
        with self.assertRaises(ValueError):
            lab.workspace_guard("/")

    def test_symlink_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            link = Path(directory) / "link"
            target = Path(directory) / "target"
            target.mkdir()
            link.symlink_to(target)
            with self.assertRaises(ValueError):
                lab.workspace_guard(link)

    def test_world_readable_workspace_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            os.chmod(directory, 0o755)
            with self.assertRaises(ValueError):
                lab.workspace_guard(directory)

    def test_missing_workspace_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(OSError):
                lab.workspace_guard(Path(directory) / "missing")

    def test_cli_missing_workspace_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing"
            result = subprocess.run([sys.executable, str(SOURCE), "--workspace", str(path)],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)

    def test_lab_stages_and_verifies(self):
        with tempfile.TemporaryDirectory() as directory:
            report = lab.lab(directory)
            self.assertEqual(report["status"], "ready")
            self.assertEqual(report["inventory"]["status"], "inspected")
            self.assertFalse(report["production_installed"])
            self.assertFalse(report["agent_enrolled"])
            self.assertFalse(report["systemd_started"])
            self.assertTrue((Path(directory) / "isolated-root").is_dir())


if __name__ == "__main__":
    unittest.main()
