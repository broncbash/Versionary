"""Regression tests for inert persistent beta staging."""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "installer/stage-beta.py"
spec = importlib.util.spec_from_file_location("arby_beta_staging", SCRIPT)
beta = importlib.util.module_from_spec(spec)
spec.loader.exec_module(beta)


class BetaStagingTests(unittest.TestCase):
    def test_refuses_live_root(self):
        with self.assertRaises(ValueError):
            beta.stage(root="/", server="https://example.test",
                       ca_cert="/missing", package="/missing")

    def test_refuses_symlinked_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "real").mkdir()
            (base / "link").symlink_to(base / "real")
            with self.assertRaises(ValueError):
                beta.stage(root=base / "link", server="https://example.test",
                           ca_cert="/missing", package="/missing")

    def test_refuses_missing_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                beta.stage(root=Path(tmp) / "not-created",
                           server="https://example.test",
                           ca_cert="/missing", package="/missing")

    def test_refuses_group_writable_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "test"
            root.mkdir()
            root.chmod(0o775)
            with self.assertRaises(ValueError):
                beta.stage(root=root, server="https://example.test",
                           ca_cert="/missing", package="/missing")

    def test_rejects_bad_url_before_any_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(beta.subprocess, "run") as run:
                with self.assertRaises((ValueError, RuntimeError)):
                    beta.stage(root=root, server="http://insecure.test",
                               ca_cert="/missing", package="/missing")
                run.assert_not_called()

    def test_cli_failure_returns_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--root", tmp,
                 "--server", "http://insecure.test", "--ca-cert", "/missing"],
                capture_output=True, text=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Beta staging failed", result.stderr)


if __name__ == "__main__":
    unittest.main()
