"""Portability regression coverage."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from agent.config import validate_server, validate_config, load_config, ConfigurationError

ROOT = Path(__file__).resolve().parents[1]

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class PortableConfigurationTests(unittest.TestCase):
    def test_domains_ips_and_ports(self):
        for value in ('https://example.com', 'https://10.2.3.4:8443', 'https://[2001:db8::1]:443'):
            self.assertEqual(validate_server(value), value)

    def test_unsafe_urls(self):
        for value in ('http://example.com', 'https://a:b@example.com', 'https://example.com/path', 'https://example.com?x=1', 'https://example.com:99999'):
            with self.assertRaises(ConfigurationError):
                validate_server(value)

    def test_config_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'config.json'
            data = {'server': 'https://test.local:9443', 'ca_cert': '/etc/versionary-agent/ca.crt'}
            path.write_text(json.dumps(data))
            self.assertEqual(load_config(path), data)

    def test_setup_rejects_conflicting_reinstall(self):
        mod = load_module('setup_config', ROOT/'installer/setup-config.py')
        with tempfile.TemporaryDirectory() as tmp:
            mod.install_config(tmp, 'https://example.org')
            mod.install_config(tmp, 'https://example.org')
            with self.assertRaises(ValueError):
                mod.install_config(tmp, 'https://other.example.org')

    def test_conflicting_reconfiguration_preserves_exact_bytes(self):
        mod = load_module('setup_config_preserve', ROOT/'installer/setup-config.py')
        with tempfile.TemporaryDirectory() as tmp:
            mod.install_config(tmp, 'https://example.org')
            config = Path(tmp) / 'etc/versionary-agent/config.json'
            before = config.read_bytes()
            with self.assertRaises(ValueError):
                mod.install_config(tmp, 'https://different.example.org')
            self.assertEqual(config.read_bytes(), before)

    def test_symlinked_configuration_rejected_without_touching_target(self):
        mod = load_module('setup_config_symlink', ROOT/'installer/setup-config.py')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_dir = root / 'etc/versionary-agent'
            config_dir.mkdir(parents=True)
            outside = root / 'outside.json'
            outside.write_text('DO NOT MODIFY')
            (config_dir / 'config.json').symlink_to(outside)
            with self.assertRaises(ValueError):
                mod.install_config(root, 'https://example.org')
            self.assertEqual(outside.read_text(), 'DO NOT MODIFY')

    def test_conflicting_ca_path_preserves_configuration(self):
        mod = load_module('setup_config_ca_conflict', ROOT/'installer/setup-config.py')
        with tempfile.TemporaryDirectory() as tmp:
            mod.install_config(tmp, 'https://example.org')
            config = Path(tmp) / 'etc/versionary-agent/config.json'
            before = config.read_bytes()
            with self.assertRaises(ValueError):
                mod.install_config(tmp, 'https://example.org',
                                   ca_cert='/etc/another-ca/ca.crt')
            self.assertEqual(config.read_bytes(), before)

    def test_generated_cert_matches_host(self):
        from cryptography import x509
        mod = load_module('generate_certs', ROOT/'installer/generate-certificates.py')
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)/'certs'
            ca, cert = mod.generate('10.20.30.40', directory)
            self.assertTrue(ca.extensions.get_extension_for_class(x509.BasicConstraints).value.ca)
            self.assertIn('10.20.30.40', str(cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value))
            self.assertEqual((directory/'server.key').stat().st_mode & 0o777, 0o600)
            with self.assertRaises(ValueError):
                mod.generate('10.20.30.40', directory)
