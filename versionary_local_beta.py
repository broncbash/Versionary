"""Localhost-only Versionary beta. No production services, no agent install."""
import argparse
import hashlib
import json
import os
import secrets
import socket
import stat
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
STATE = ROOT / '.versionary-local-beta'
DB = STATE / 'agents.db'
AUTH = STATE / 'admin-token'
AGENT = STATE / 'agent.json'


def private_state():
    STATE.mkdir(mode=0o700, exist_ok=True)
    os.chmod(STATE, 0o700)


def private_write(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        stream.write(value)


def configure():
    import agent_registry
    agent_registry.DB_PATH = DB
    return agent_registry


def create_app():
    private_state()
    registry = configure()
    registry.initialize_database()
    from fastapi import FastAPI
    from admin_agents_api import router as inventory_router
    from dashboard_ui import router as dashboard_router
    from agent_reporting_api import router as reporting_router
    from agent_enrollment_api import router as credential_router
    app = FastAPI(title='Versionary Local Beta', docs_url=None, redoc_url=None)
    for router in (inventory_router, dashboard_router, reporting_router, credential_router):
        app.include_router(router)
    @app.get('/health')
    def health():
        return {'status': 'online', 'mode': 'localhost-development-beta', 'production': False}
    return app


def initialize():
    private_state()
    registry = configure()
    registry.initialize_database()
    if not AUTH.exists():
        private_write(AUTH, secrets.token_urlsafe(36) + '\n')
    if not AGENT.exists():
        from pathlib import Path
        os_release = Path('/etc/os-release')
        data = os_release.read_text() if os_release.exists() else ''
        distro = next((line.split('=',1)[1].strip().strip('"') for line in data.splitlines() if line.startswith('ID=')), 'linux')
        agent_id = registry.register_agent(socket.gethostname(), distro)
        if not registry.approve_agent(agent_id):
            raise RuntimeError('Agent approval failed')
        token = registry.issue_agent_credential(agent_id)
        if not token:
            raise RuntimeError('Agent credential issuance failed')
        private_write(AGENT, json.dumps({'id': agent_id, 'token': token, 'distro': distro}) + '\n')
    print('Local beta initialized. No services started.')
    print('Dashboard token (keep private):', AUTH.read_text().strip())
    print('Dashboard: http://127.0.0.1:8765/admin/dashboard')


def scan():
    if not AGENT.exists() or not AUTH.exists():
        raise SystemExit('First run: python versionary_local_beta.py init')
    from fastapi.testclient import TestClient
    from scanner import scan_arch_updates
    app = create_app()
    agent = json.loads(AGENT.read_text())
    os.environ['ARBY_AGENT_REPORTING_ENABLED'] = 'true'
    os.environ['ARBY_ADMIN_TOKEN_HASH'] = hashlib.sha256(AUTH.read_text().strip().encode()).hexdigest()
    result = scan_arch_updates()
    payload = {'status': result['status'], 'packages': result['packages'], 'error': result.get('error')}
    with TestClient(app) as client:
        headers = {'Authorization': 'Bearer ' + agent['token']}
        heartbeat = client.post(f"/api/v1/agents/{agent['id']}/heartbeat", headers=headers)
        report = client.post(f"/api/v1/agents/{agent['id']}/report", headers=headers, json=payload)
        inventory = client.get('/api/v1/admin/agents', headers={'Authorization': 'Bearer ' + AUTH.read_text().strip()})
        if (heartbeat.status_code, report.status_code, inventory.status_code) != (200, 201, 200):
            raise SystemExit(f'API verification failed: {heartbeat.status_code}, {report.status_code}, {inventory.status_code}')
        agents = inventory.json()['agents']
        matched = next((a for a in agents if a['id'] == agent['id']), None)
        if not matched or matched['scan_status'] != result['status']:
            raise SystemExit('Inventory mismatch')
        print(json.dumps({'distro': agent['distro'], 'scanner_status': result['status'], 'updates': matched['updates'], 'health': matched['health'], 'error': result.get('error')}, indent=2))


def serve():
    if not AUTH.exists():
        raise SystemExit('First run: python versionary_local_beta.py init')
    os.environ['ARBY_ADMIN_TOKEN_HASH'] = hashlib.sha256(AUTH.read_text().strip().encode()).hexdigest()
    # Reporting remains disabled in the browser-facing server. Only explicit local scan CLI enables it.
    os.environ['ARBY_AGENT_REPORTING_ENABLED'] = 'false'
    os.environ['ARBY_SETTINGS_RUNTIME_ENABLED'] = 'false'
    import uvicorn
    uvicorn.run(create_app(), host='127.0.0.1', port=8765, log_level='info')


def main():
    parser = argparse.ArgumentParser(description='Versionary isolated localhost beta')
    parser.add_argument('command', choices=('init','scan','serve','status'))
    args = parser.parse_args()
    if args.command == 'init': initialize()
    elif args.command == 'scan': scan()
    elif args.command == 'serve': serve()
    else:
        print('State:', STATE)
        print('Database exists:', DB.exists())
        print('Agent enrolled:', AGENT.exists())

if __name__ == '__main__':
    main()
