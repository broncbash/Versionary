"""Safety and identity checks for opt-in local observer controls."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import versionary_beta_control as control


class BetaControlTests(unittest.TestCase):
    def test_status_does_not_reveal_agent_token(self):
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp)
            (state / 'agent.json').write_text(json.dumps({'id': 'example-id', 'distro': 'cachyos', 'token': 'VERY-SECRET'}))
            with patch.object(control.beta, 'STATE', state), patch.object(control.beta, 'AGENT', state / 'agent.json'), patch.object(control.beta, 'AUTH', state / 'admin-token'), patch.object(control.beta, 'DB', state / 'agents.db'):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    control.status()
                self.assertIn('cachyos', output.getvalue())
                self.assertNotIn('VERY-SECRET', output.getvalue())

    def test_preview_is_inert_and_private(self):
        source = Path(control.__file__).read_text()
        self.assertNotIn('systemctl', source)
        self.assertNotIn('pacman -Syu', source)
        self.assertIn('NoNewPrivileges=yes', source)
        self.assertIn('Persistent=false', source)
        self.assertIn('0o600', source)

    def test_identity_persists_existing_agent_id(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'agent.json'
            path.write_text(json.dumps({'id': 'fixed-id', 'distro': 'cachyos', 'token': 'secret'}))
            with patch.object(control.beta, 'AGENT', path):
                self.assertEqual(control.identity()['id'], 'fixed-id')
                self.assertEqual(control.identity()['id'], 'fixed-id')


if __name__ == '__main__':
    unittest.main()
