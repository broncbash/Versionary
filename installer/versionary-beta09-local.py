#!/usr/bin/env python3
"""Local, persistent Versionary Beta 0.9 operator CLI. No root or services."""
import argparse, hashlib, json, os, secrets, socket, ssl, subprocess, sys, urllib.request, uuid
from pathlib import Path

REPO=Path.home()/"Projects/arby-patch-command"
STATE=Path.home()/".local/state/versionary-beta09"
PORT=8769
URL=f"https://localhost:{PORT}"

def require_repo():
    if not (REPO/'main.py').is_file() or not (REPO/'.venv/bin/python').exists():
        raise RuntimeError(f"Missing Versionary repository or venv: {REPO}")

def prepare():
    require_repo()
    STATE.mkdir(parents=True,exist_ok=True,mode=0o700)
    STATE.chmod(0o700)
    cert,key=STATE/'server.crt',STATE/'server.key'
    if not cert.exists() or not key.exists():
        if cert.exists() or key.exists():
            raise RuntimeError('Partial TLS certificate/key; refusing overwrite')
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),'-out',str(cert),'-days','365','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost,IP:127.0.0.1'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        key.chmod(0o600)
    tokenfile=STATE/'admin.token'
    if not tokenfile.exists():
        tokenfile.write_text(secrets.token_urlsafe(32)+'\n')
        tokenfile.chmod(0o600)
    return tokenfile.read_text().strip()

def config(token):
    os.environ.update(ARBY_ADMIN_TOKEN_HASH=hashlib.sha256(token.encode()).hexdigest(),ARBY_AGENT_REGISTRATION_ENABLED='true',ARBY_AGENT_REPORTING_ENABLED='true',ARBY_ENROLLMENT_V2_ENABLED='false',ARBY_SETTINGS_RUNTIME_ENABLED='false')

def server():
    token=prepare();config(token)
    sys.path.insert(0,str(REPO))
    import agent_registry
    agent_registry.DB_PATH=STATE/'agents.db'
    agent_registry.initialize_database()
    from main import app
    import uvicorn
    print(f'\nVERSIONARY PERSISTENT LOCAL BETA\nDashboard: {URL}/admin/dashboard\nAdmin token: {token}\nState: {STATE}\nCtrl+C stops server; data remains.\n',flush=True)
    uvicorn.run(app,host='127.0.0.1',port=PORT,ssl_certfile=str(STATE/'server.crt'),ssl_keyfile=str(STATE/'server.key'),log_level='warning')

def api(method,path,payload=None,token=None):
    if not (STATE/'server.crt').exists():raise RuntimeError('Run install first')
    ctx=ssl.create_default_context(cafile=str(STATE/'server.crt'))
    data=None if payload is None else json.dumps(payload).encode()
    headers={'Content-Type':'application/json'}
    if token:headers['Authorization']='Bearer '+token
    req=urllib.request.Request(URL+path,data,headers,method=method)
    with urllib.request.urlopen(req,context=ctx,timeout=15) as response:return json.load(response)

def agentfile():return STATE/'desktop-agent.json'

def register():
    require_repo()
    if agentfile().exists():
        print('Already registered:',json.loads(agentfile().read_text())['agent_id']);return
    aid=str(uuid.uuid4())
    r=api('POST','/api/v1/agents/register',{'hostname':socket.gethostname(),'platform':'arch','agent_id':aid})
    agentfile().write_text(json.dumps({'agent_id':aid},indent=2)+'\n');agentfile().chmod(0o600)
    print('Registered:',r['agent_id'],'status:',r['status'])
    print('Approve in dashboard, then run: activate')

def activate():
    # Local-only administrative credential handoff; requires access to the private state directory.
    require_repo()
    aid=json.loads(agentfile().read_text())['agent_id']
    admin=(STATE/'admin.token').read_text().strip()
    result=api('POST',f'/api/v1/agents/{aid}/credential',token=admin)
    path=agentfile();path.write_text(json.dumps({'agent_id':aid,'token':result['token']},indent=2)+'\n');path.chmod(0o600)
    print('Credential issued to locally registered, approved desktop agent.')
    print('Run: report')

def report():
    obj=json.loads(agentfile().read_text());aid=obj['agent_id'];token=obj.get('token')
    if not token:raise RuntimeError('Approve agent and run activate first')
    hb=api('POST',f'/api/v1/agents/{aid}/heartbeat',token=token)
    if hb.get('status')!='ok':raise RuntimeError('Heartbeat failed')
    result=subprocess.run(['checkupdates'],capture_output=True,text=True,timeout=120)
    if result.returncode not in (0,2):raise RuntimeError('checkupdates failed: '+result.stderr[:300])
    packages=[]
    for line in result.stdout.splitlines():
        parts=line.split()
        if len(parts)>=4 and parts[2]=='->':packages.append({'name':parts[0],'installed':parts[1],'available':parts[3]})
    if len(packages)>5000:raise RuntimeError('Too many packages for beta report')
    result=api('POST',f'/api/v1/agents/{aid}/report',{'status':'success','packages':packages},token=token)
    print(f'Heartbeat OK; {len(packages)} actual desktop updates; server: {result["status"]}')
    print('Refresh dashboard fleet (reenter token after browser page reload).')

def main():
    parser=argparse.ArgumentParser(description='Versionary Beta 0.9 persistent LOCAL operator')
    parser.add_argument('command',choices=['install','server','register','activate','report','status'])
    args=parser.parse_args()
    if args.command=='install':
        prepare();print('Installed persistent local state:',STATE);print('Next: server')
    elif args.command=='server':server()
    elif args.command=='register':register()
    elif args.command=='activate':activate()
    elif args.command=='report':report()
    elif args.command=='status':
        print('State:',STATE,'exists:',STATE.is_dir())
        print('Agent:',agentfile().exists())
        print('Dashboard:',URL+'/admin/dashboard')
if __name__=='__main__':
    try:main()
    except (OSError,RuntimeError,ValueError,KeyError,subprocess.CalledProcessError) as exc:
        print('ERROR:',exc,file=sys.stderr);sys.exit(1)
