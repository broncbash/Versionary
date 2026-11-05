import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from server_settings import save

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'installer' / 'settings-preflight.py'
spec = importlib.util.spec_from_file_location('arby_settings_preflight', SCRIPT)
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)

class SettingsPreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'settings.json'

    def test_missing_settings_defaults_ready_for_offline_staging(self):
        result = preflight.inspect(self.path)
        self.assertTrue(result['ready'])
        self.assertFalse(result['applied'])

    def test_missing_url_blocks_network_readiness(self):
        self.assertFalse(preflight.inspect(self.path, require_network=True)['ready'])

    def test_valid_https_url_passes_network_readiness(self):
        save({'public_url': 'https://patch.example.test'}, self.path)
        self.assertTrue(preflight.inspect(self.path, require_network=True)['ready'])

    def test_invalid_json_fails_closed(self):
        self.path.write_text('{bad json')
        os.chmod(self.path, 0o600)
        with self.assertRaises(ValueError):
            preflight.inspect(self.path)

    def test_insecure_permissions_fails_closed(self):
        self.path.write_text('{}')
        os.chmod(self.path, 0o644)
        with self.assertRaises(ValueError):
            preflight.inspect(self.path)

    def test_cli_nonzero_when_network_not_ready(self):
        run = subprocess.run([sys.executable, str(SCRIPT), '--path', str(self.path), '--require-network'],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 1)
        self.assertFalse(json.loads(run.stdout)['ready'])

    def test_cli_read_only(self):
        save({'appearance': 'dark'}, self.path)
        before = self.path.read_bytes()
        run = subprocess.run([sys.executable, str(SCRIPT), '--path', str(self.path)],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(self.path.read_bytes(), before)
