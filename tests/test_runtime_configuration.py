import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from runtime_configuration import effective_flags
from server_settings import DEFAULTS


class RuntimeConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'settings.json'
        self.path.write_text(json.dumps({**DEFAULTS, 'public_url': 'https://patch.example.test',
                                         'enrollment_enabled': True, 'reporting_enabled': True}))
        os.chmod(self.path, 0o600)

    def test_disabled_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(effective_flags(self.path)['registration_enabled'])

    def test_runtime_gate_alone_not_sufficient(self):
        with patch.dict(os.environ, {'ARBY_SETTINGS_RUNTIME_ENABLED': 'true'}, clear=True):
            self.assertFalse(effective_flags(self.path)['reporting_enabled'])

    def test_all_gates_enable(self):
        env = {'ARBY_SETTINGS_RUNTIME_ENABLED': 'true',
               'ARBY_AGENT_REGISTRATION_ENABLED': 'true',
               'ARBY_AGENT_REPORTING_ENABLED': 'true'}
        with patch.dict(os.environ, env, clear=True):
            self.assertTrue(effective_flags(self.path)['registration_enabled'])
            self.assertTrue(effective_flags(self.path)['reporting_enabled'])

    def test_invalid_file_fails_closed(self):
        self.path.write_text('{bad json')
        with patch.dict(os.environ, {'ARBY_SETTINGS_RUNTIME_ENABLED': 'true',
                                     'ARBY_AGENT_REGISTRATION_ENABLED': 'true'}, clear=True):
            self.assertFalse(effective_flags(self.path)['registration_enabled'])
            self.assertFalse(effective_flags(self.path)['configuration_valid'])

    def test_missing_public_url_fails_closed(self):
        self.path.write_text(json.dumps({**DEFAULTS, 'enrollment_enabled': False}))
        with patch.dict(os.environ, {'ARBY_SETTINGS_RUNTIME_ENABLED': 'true',
                                     'ARBY_AGENT_REGISTRATION_ENABLED': 'true'}, clear=True):
            self.assertFalse(effective_flags(self.path)['registration_enabled'])

    def test_disabled_settings_override_environment(self):
        self.path.write_text(json.dumps({**DEFAULTS, 'public_url': 'https://patch.example.test'}))
        with patch.dict(os.environ, {'ARBY_SETTINGS_RUNTIME_ENABLED': 'true',
                                     'ARBY_AGENT_REGISTRATION_ENABLED': 'true',
                                     'ARBY_AGENT_REPORTING_ENABLED': 'true'}, clear=True):
            self.assertFalse(effective_flags(self.path)['registration_enabled'])
            self.assertFalse(effective_flags(self.path)['reporting_enabled'])
