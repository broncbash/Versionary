import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "installer"))
import importlib.util

class DashboardDemoTests(unittest.TestCase):
    def test_preview_is_safe(self):
        result = subprocess.run([sys.executable, str(ROOT / "installer/versionary-dashboard-demo.py"),
                                 "--preview"], capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("localhost only", result.stdout)

    def test_demo_populates_disposable_database(self):
        spec = importlib.util.spec_from_file_location("versionary_dashboard_demo",
                                                       ROOT / "installer/versionary-dashboard-demo.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        import agent_registry
        with tempfile.TemporaryDirectory(prefix="versionary-demo-test-") as tmp:
            with patch.object(agent_registry, "DB_PATH", Path(tmp) / "agents.db"):
                pending, approved = module.populate_demo(Path(tmp) / "agents.db")
                self.assertNotEqual(pending, approved)
                self.assertFalse(agent_registry.is_agent_approved(pending))
                self.assertTrue(agent_registry.is_agent_approved(approved))
