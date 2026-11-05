"""Batch 8C.1: destination conflicts must be rejected before subprocesses."""
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1] / 'installer'
def load(filename, alias):
    spec = importlib.util.spec_from_file_location(alias, HERE / filename)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj

preflight = load('beta-preflight.py', 'beta_preflight_test')

class BetaPreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.modules = {name: b'payload-'+name.encode() for name in load('install-files.py','beta_files_test').MODULES}
        self.package = self.root / 'package.tar.gz'
        self.package.write_bytes(b'fixture')
        self.ca = b'CA fixture'
        self.server = 'https://patch.example.test'
        self.validator = patch.object(preflight, 'load', side_effect=self.mock_load)
        self.validator.start()
        self.addCleanup(self.validator.stop)
    def mock_load(self, name, alias):
        if name == 'validate-package.py':
            return type('V', (), {'load_modules': lambda _, p: self.modules})()
        return load(name, alias)
    def inspect(self):
        return preflight.inspect(self.root, self.server, self.ca, self.package)
    def write(self, relative, payload):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        return path
    def test_empty_root_passes_without_changes(self):
        self.assertFalse(self.inspect()['changes_made'])
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ['package.tar.gz'])
    def test_conflicting_ca(self):
        self.write('etc/versionary-agent/ca.crt', b'wrong')
        with self.assertRaisesRegex(ValueError, 'CA differs'): self.inspect()
    def test_matching_ca(self):
        self.write('etc/versionary-agent/ca.crt', self.ca)
        self.inspect()
    def test_conflicting_config(self):
        self.write('etc/versionary-agent/config.json', b'{"server":"wrong"}')
        with self.assertRaisesRegex(ValueError, 'configuration differs'): self.inspect()
    def test_matching_config(self):
        self.write('etc/versionary-agent/config.json', json.dumps({'server':self.server,'ca_cert':'/etc/versionary-agent/ca.crt'}).encode())
        self.inspect()
    def test_corrupt_config(self):
        self.write('etc/versionary-agent/config.json', b'not-json')
        with self.assertRaisesRegex(ValueError, 'Invalid existing'): self.inspect()
    def test_conflicting_unit(self):
        self.write('etc/systemd/system/versionary-agent.timer', b'wrong')
        with self.assertRaisesRegex(ValueError, 'systemd unit differs'): self.inspect()
    def test_matching_unit(self):
        self.write('etc/systemd/system/versionary-agent.timer', (HERE/'systemd/versionary-agent.timer').read_bytes())
        self.inspect()
    def test_symlink_ancestor(self):
        (self.root/'etc').symlink_to(self.root)
        with self.assertRaisesRegex(ValueError, 'Unsafe beta directory'): self.inspect()
    def test_symlink_ca(self):
        target = self.write('external', b'CA')
        path = self.root/'etc/versionary-agent/ca.crt'
        path.parent.mkdir(parents=True)
        path.symlink_to(target)
        with self.assertRaisesRegex(ValueError, 'Unsafe beta destination'): self.inspect()
    def test_hardlinked_config(self):
        target = self.write('external', b'{}')
        path = self.root/'etc/versionary-agent/config.json'
        path.parent.mkdir(parents=True)
        os.link(target, path)
        with self.assertRaisesRegex(ValueError, 'Unsafe beta destination'): self.inspect()
    def test_wrong_active_release(self):
        app = self.root/'opt/versionary-agent'
        app.mkdir(parents=True)
        (app/'agent').symlink_to('releases/wrong/agent')
        with self.assertRaisesRegex(ValueError, 'release differs'): self.inspect()
    def test_unactivated_release(self):
        release = load('atomic-release.py','beta_release_test')
        (self.root/'opt/versionary-agent/releases'/release.release_id(self.modules)).mkdir(parents=True)
        with self.assertRaisesRegex(ValueError, 'Unactivated'): self.inspect()
    def test_root_rejected(self):
        with self.assertRaises(ValueError): preflight.inspect('/',self.server,self.ca,self.package)

if __name__ == '__main__': unittest.main()
