#!/usr/bin/env python3
"""Disposable localhost HTTPS trial: genuine desktop package inventory, no agent installation."""
import hashlib, json, os, secrets, socket, ssl, subprocess, sys, tempfile, threading, time
import urllib.error, urllib.request, uuid
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

def request(method, path, payload=None, token=None, context=None):
    body=None if payload is None else json.dumps(payload).encode()
    headers={"Content-Type":"application/json"}
    if token: headers["Authorization"]="Bearer "+token
    req=urllib.request.Request("https://localhost:8769"+path,body,headers,method=method)
    with urllib.request.urlopen(req,context=context,timeout=8) as response:
        return json.load(response)

def updates():
    # pacman -Qu only queries local package database; never syncs, installs or elevates.
    p=subprocess.run(["pacman","-Qu"],capture_output=True,text=True,timeout=30,check=False)
    if p.returncode not in (0,1):
        raise RuntimeError("pacman -Qu failed: "+p.stderr[:200])
    result=[]
    for line in p.stdout.splitlines():
        parts=line.split()
        if len(parts)>=4 and parts[2]=="->":
            result.append({"name":parts[0],"installed":parts[1],"available":parts[3]})
    return result[:5000]

def main():
    import agent_registry, uvicorn
    with tempfile.TemporaryDirectory(prefix="versionary-real-agent-trial-") as d:
        root=Path(d); cert=root/"server.crt"; key=root/"server.key"
        cmd=["openssl","req","-x509","-newkey","rsa:2048","-nodes",
             "-keyout",str(key),"-out",str(cert),"-days","1",
             "-subj","/CN=localhost",
             "-addext","subjectAltName=DNS:localhost,IP:127.0.0.1"]
        subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        agent_registry.DB_PATH=root/"agents.db"
        agent_registry.initialize_database()
        admin=secrets.token_urlsafe(32)
        os.environ.update(ARBY_ADMIN_TOKEN_HASH=hashlib.sha256(admin.encode()).hexdigest(),
            ARBY_AGENT_REGISTRATION_ENABLED="true",ARBY_AGENT_REPORTING_ENABLED="true",
            ARBY_ENROLLMENT_V2_ENABLED="false",ARBY_SETTINGS_RUNTIME_ENABLED="false")
        from main import app
        config=uvicorn.Config(app,host="127.0.0.1",port=8769,ssl_certfile=str(cert),
            ssl_keyfile=str(key),log_level="error")
        server=uvicorn.Server(config)
        t=threading.Thread(target=server.run,daemon=True);t.start()
        try:
            for _ in range(80):
                if server.started:break
                time.sleep(.1)
            if not server.started:raise RuntimeError("HTTPS server failed to start (is port 8769 in use?)")
            ctx=ssl.create_default_context(cafile=str(cert))
            print("\nVERSIONARY — LOCAL HTTPS REAL-AGENT TRIAL",flush=True)
            print("Dashboard: https://localhost:8769/admin/dashboard")
            print("Admin token: "+admin)
            print("Only loopback HTTPS, temporary files, and pacman -Qu (read-only).")
            print("No service install, no sudo, no package modification, no homelab access.\n")
            hostname=socket.gethostname()
            agent_id=str(uuid.uuid4())
            result=request("POST","/api/v1/agents/register",
                {"hostname":hostname,"platform":"arch","agent_id":agent_id},context=ctx)
            print("Registered real desktop as PENDING:",result["agent_id"])
            print("\n1. Open the dashboard URL and enter the admin token.")
            print("2. Click Refresh fleet, then Approve agent.")
            input("\nPress ENTER after approval to continue...")
            inventory=request("GET","/api/v1/admin/agents",token=admin,context=ctx)
            approved=agent_registry.is_agent_approved(agent_id)
            if not approved:
                print("Not approved yet. Return to dashboard, approve, then rerun trial.")
                return 2
            cred=request("POST",f"/api/v1/agents/{agent_id}/credential",token=admin,context=ctx)
            agent_token=cred["token"]
            heartbeat=request("POST",f"/api/v1/agents/{agent_id}/heartbeat",token=agent_token,context=ctx)
            print("Heartbeat:",heartbeat["status"])
            packages=updates()
            report=request("POST",f"/api/v1/agents/{agent_id}/report",
                {"status":"success","packages":packages},token=agent_token,context=ctx)
            print(f"REAL DESKTOP UPDATE REPORT: {len(packages)} available updates; server {report['status']}")
            print("Refresh the dashboard to view the report.")
            input("\nPress ENTER to end trial and erase temporary server/database/certificate...")
            return 0
        finally:
            server.should_exit=True
            t.join(timeout=5)
if __name__=="__main__":
    try:raise SystemExit(main())
    except KeyboardInterrupt:print("\nTrial stopped; temporary files cleaned.")
    except Exception as exc:
        print(f"\nTRIAL ERROR: {exc}",file=sys.stderr)
        raise SystemExit(1)
