"""First-run UX and explicitly gated enrollment v2 in the actual FastAPI app."""
import subprocess
import sys
import unittest
from pathlib import Path
from fastapi.testclient import TestClient
from main import app

ROOT = Path(__file__).resolve().parents[1]

class FirstRunAcceptance(unittest.TestCase):
    def test_guide_runs_without_network_or_state(self):
        result = subprocess.run(
            [sys.executable, "-B", str(ROOT / "installer/versionary-first-run.py"),
             "--guide", "--state-dir", "/tmp/versionary-guide-only"],
            capture_output=True, text=True, timeout=15, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Administrator approval", result.stdout)
        self.assertIn("No patch installation", result.stdout)
        self.assertIn("0. Exit", result.stdout)

    def test_no_tty_refuses_interactive_mode(self):
        result = subprocess.run(
            [sys.executable, "-B", str(ROOT / "installer/versionary-first-run.py")],
            input="", capture_output=True, text=True, timeout=15, check=False)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Interactive terminal required", result.stderr)

    def test_actual_server_exposes_gated_v2_registration(self):
        with TestClient(app) as client:
            # The v2 feature gate is disabled unless explicitly enabled.
            from unittest.mock import patch
            with patch.dict("os.environ", {"ARBY_ENROLLMENT_V2_ENABLED": "false"}):
                response = client.post("/api/v2/agents/register", json={
                    "agent_id": "00000000-0000-4000-8000-000000000001",
                    "hostname": "beta", "platform": "arch",
                    "public_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
                })
            self.assertEqual(response.status_code, 503)
