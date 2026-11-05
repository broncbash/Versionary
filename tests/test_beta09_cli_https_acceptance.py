"""Real subprocess agent CLI -> verified loopback HTTPS -> server inventory.

No external network, no system services, no real package scan or deployment.
"""
import hashlib
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
import agent_registry
from main import app as production_app
from tests.test_beta_tls_journey import BetaTLSJourney

ROOT = Path(__file__).resolve().parents[1]


class Beta09CLIHTTPSAcceptance(BetaTLSJourney):
    def setUp(self):
        # Reuse the existing verified-TLS disposable server fixture without
        # inheriting its test methods or duplicating its existing assertions.
        BetaTLSJourney.setUp(self)
        self.admin_token = 'disposable-batch4-admin'
        self.admin_env = patch.dict(os.environ, {
            'ARBY_ADMIN_TOKEN_HASH': hashlib.sha256(self.admin_token.encode()).hexdigest(),
        })
        self.admin_env.start()
        self.addCleanup(self.admin_env.stop)
        self.inventory = TestClient(production_app)
        self.addCleanup(self.inventory.close)
        self.cli_state = self.root / 'cli-state'

    def cli(self, command, *arguments):
        env = dict(os.environ)
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        env['NO_PROXY'] = '127.0.0.1,localhost'
        env['no_proxy'] = '127.0.0.1,localhost'
        return subprocess.run(
            [sys.executable, '-B', 'versionary_agent_cli.py',
             '--state-dir', str(self.cli_state), command, *arguments],
            cwd=ROOT, env=env, capture_output=True, text=True,
            timeout=30, check=False,
        )

    def assert_cli(self, command, *args):
        result = self.cli(command, *args)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def inventory_row(self):
        response = self.inventory.get('/api/v1/admin/agents', headers={
            'Authorization': 'Bearer ' + self.admin_token,
        })
        self.assertEqual(response.status_code, 200, response.text)
        rows = response.json()['agents']
        self.assertEqual(len(rows), 1)
        return rows[0]

    def test_subprocess_cli_enroll_heartbeat_and_dashboard_inventory(self):
        self.assert_tls_ready()
        self.assert_cli('setup', '--server', self.server_url,
                        '--ca-cert', str(self.certs / 'ca.crt'))
        registered = self.assert_cli('register')
        self.assertIn('pending', registered)
        pending = self.inventory_row()
        self.assertEqual(pending['status'], 'pending')
        self.assertEqual(pending['health'], 'pending')
        agent_id = pending['id']
        self.assertTrue(agent_registry.approve_agent(agent_id))
        enrolled = self.assert_cli('enroll')
        self.assertIn('enrolled', enrolled)
        heartbeat = self.assert_cli('heartbeat')
        self.assertIn('ok', heartbeat)
        active = self.inventory_row()
        self.assertEqual(active['id'], agent_id)
        self.assertEqual(active['status'], 'approved')
        self.assertEqual(active['health'], 'online')
        # The actual agent transport reports a synthetic update; never scan host.
        from agent.credentials import load_credential
        from agent.reporting import send_report
        from agent.identity import load_identity
        token = load_credential(self.cli_state / 'credential.json')
        identity = load_identity(self.cli_state / 'identity.json')
        result = send_report(identity, token, {
            'status': 'success',
            'packages': [{'name': 'disposable-demo-package',
                          'installed': '1.0', 'available': '1.1'}],
            'error': None,
        }, server=self.server_url, ca_cert=self.certs / 'ca.crt')
        self.assertEqual(result['status'], 'recorded')
        reported = self.inventory_row()
        self.assertEqual(reported['updates'], 1)
        self.assertEqual(reported['scan_status'], 'success')
        dashboard = self.inventory.get('/admin/dashboard')
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn('Versionary', dashboard.text)
        self.assertNotIn(token, dashboard.text)
        self.assertTrue(agent_registry.revoke_agent(agent_id))
        rejected = self.cli('heartbeat')
        self.assertNotEqual(rejected.returncode, 0)
        self.assertEqual(self.inventory_row()['health'], 'revoked')

    def test_cli_setup_rejects_untrusted_missing_ca_without_state(self):
        failed = self.cli('setup', '--server', self.server_url,
                          '--ca-cert', str(self.root / 'missing-ca.crt'))
        self.assertNotEqual(failed.returncode, 0)
        self.assertFalse((self.cli_state / 'config.json').exists())


if __name__ == '__main__':
    unittest.main()
