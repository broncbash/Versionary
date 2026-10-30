"""Explicit opt-in real Arch update scan, isolated API transport and DB.

Run with VERSIONARY_REAL_ARCH_SCAN=1; excluded from default test discovery.
"""
import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import agent_registry
from main import app
from scanner import scan_arch_updates


@unittest.skipUnless(os.environ.get('VERSIONARY_REAL_ARCH_SCAN') == '1', 'real scan requires explicit opt-in')
class VersionaryRealArchScan(unittest.TestCase):
    def test_real_scan_to_authenticated_inventory(self):
        with tempfile.TemporaryDirectory(prefix='versionary-arch-') as tmp:
            db = Path(tmp) / 'agents.db'
            admin_token = 'disposable-versionary-admin-token'
            env = {
                'ARBY_AGENT_REPORTING_ENABLED': 'true',
                'ARBY_SETTINGS_RUNTIME_ENABLED': 'false',
                'ARBY_ADMIN_TOKEN_HASH': hashlib.sha256(admin_token.encode()).hexdigest(),
            }
            with patch.dict(os.environ, env), patch.object(agent_registry, 'DB_PATH', db):
                agent_registry.initialize_database()
                agent_id = agent_registry.register_agent('local-arch-desktop', 'arch')
                self.assertTrue(agent_registry.approve_agent(agent_id))
                agent_token = agent_registry.issue_agent_credential(agent_id)
                self.assertTrue(agent_token)
                with TestClient(app) as client:
                    heartbeat = client.post(f'/api/v1/agents/{agent_id}/heartbeat', headers={'Authorization': f'Bearer {agent_token}'})
                    self.assertEqual(heartbeat.status_code, 200, heartbeat.text)
                    result = scan_arch_updates()
                    self.assertIn(result['status'], ('success', 'error'))
                    self.assertLessEqual(len(result['packages']), 5000, 'Too many packages for API report; nothing submitted')
                    payload = {'status': result['status'], 'packages': result['packages'], 'error': result.get('error')}
                    report = client.post(f'/api/v1/agents/{agent_id}/report', headers={'Authorization': f'Bearer {agent_token}'}, json=payload)
                    self.assertEqual(report.status_code, 201, report.text)
                    inventory = client.get('/api/v1/admin/agents', headers={'Authorization': f'Bearer {admin_token}'})
                    self.assertEqual(inventory.status_code, 200, inventory.text)
                    agents = inventory.json()['agents']
                    self.assertEqual(len(agents), 1)
                    agent = agents[0]
                    self.assertEqual(agent['hostname'], 'local-arch-desktop')
                    self.assertEqual(agent['health'], 'online')
                    self.assertEqual(agent['scan_status'], result['status'])
                    if result['status'] == 'success':
                        self.assertEqual(agent['updates'], len(result['packages']))
                    else:
                        self.assertIsNone(agent['updates'])
                    dashboard = client.get('/admin/dashboard')
                    self.assertEqual(dashboard.status_code, 200)
                    self.assertIn('Agent Fleet', dashboard.text)
                    self.assertEqual(client.get('/api/v1/admin/agents').status_code, 401)
                    self.assertEqual(client.post(f'/api/v1/agents/{agent_id}/report', json=payload).status_code, 401)
                    print('\nVERSIONARY REAL ARCH SCAN:', {'scanner_status': result['status'], 'reported_updates': agent['updates'], 'health': agent['health'], 'scanner_error': result.get('error')})
