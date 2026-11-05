import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from certificate_renewal import renew, RenewalError
from certificate_management import validate_files

spec = importlib.util.spec_from_file_location('generate_certificates', Path(__file__).resolve().parents[1] / 'installer/generate-certificates.py')
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)

class RenewalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.ca = self.root / 'ca'
        gen.generate('old.example.test', self.ca)
        self.dest = self.root / 'renewed'
        self.dest.mkdir(mode=0o700)

    def run_renew(self, hostname='new.example.test', **kw):
        return renew(self.ca/'ca.crt', self.ca/'ca.key', hostname, self.dest, **kw)

    def test_renew_and_validate(self):
        result = self.run_renew()
        self.assertFalse(result['applied'])
        validate_files(self.dest/'server.crt', self.dest/'server.key', 'new.example.test')
        self.assertEqual((self.dest/'server.key').stat().st_mode & 0o777, 0o600)

    def test_refuses_overwrite(self):
        self.run_renew()
        with self.assertRaises(FileExistsError):
            self.run_renew()

    def test_refuses_public_directory(self):
        self.dest.chmod(0o755)
        with self.assertRaises(RenewalError):
            self.run_renew()

    def test_rejects_invalid_host(self):
        with self.assertRaises(RenewalError):
            self.run_renew('bad..name')

    def test_rejects_invalid_lifetime(self):
        with self.assertRaises(RenewalError):
            self.run_renew(days=826)

    def test_rejects_wrong_ca_key(self):
        other = self.root/'other'
        gen.generate('other.example.test', other)
        with self.assertRaises(RenewalError):
            renew(self.ca/'ca.crt', other/'ca.key', 'new.example.test', self.dest)
        self.assertFalse((self.dest/'server.crt').exists())

    def test_rejects_insecure_ca_key(self):
        (self.ca/'ca.key').chmod(0o644)
        with self.assertRaises(RenewalError):
            self.run_renew()
