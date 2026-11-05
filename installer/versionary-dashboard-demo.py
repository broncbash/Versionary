#!/usr/bin/env python3
"""Versionary disposable, loopback-only dashboard demonstration."""
import argparse
import hashlib
import os
import secrets
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def populate_demo(db):
    import agent_registry
    agent_registry.DB_PATH = db
    agent_registry.initialize_database()
    pending = agent_registry.register_agent("pending-beta-agent", "debian")
    approved = agent_registry.register_agent("reporting-beta-agent", "arch")
    if not agent_registry.approve_agent(approved):
        raise RuntimeError("Demo approval failed")
    token = agent_registry.issue_agent_credential(approved)
    if not token:
        raise RuntimeError("Demo credential failed")
    if not agent_registry.record_agent_heartbeat(approved, token):
        raise RuntimeError("Demo heartbeat failed")
    if not agent_registry.record_agent_scan(approved, token, "success", []):
        raise RuntimeError("Demo report failed")
    return pending, approved

def main(argv=None):
    parser = argparse.ArgumentParser(description="Versionary disposable dashboard demonstration")
    parser.add_argument("--port", type=int, default=8769)
    parser.add_argument("--preview", action="store_true", help="Explain the demo without creating files")
    args = parser.parse_args(argv)
    if not 1024 <= args.port <= 65535:
        parser.error("port must be 1024..65535")
    if args.preview:
        print("Versionary dashboard demo: localhost only, temporary database, two sample agents.")
        print("No live installation, patching, reboot, systemd activation, or homelab changes.")
        return 0
    with tempfile.TemporaryDirectory(prefix="versionary-dashboard-demo-") as directory:
        db = Path(directory) / "agents.db"
        admin_token = secrets.token_urlsafe(32)
        os.environ["ARBY_ADMIN_TOKEN_HASH"] = hashlib.sha256(admin_token.encode()).hexdigest()
        os.environ["ARBY_AGENT_REGISTRATION_ENABLED"] = "false"
        os.environ["ARBY_AGENT_REPORTING_ENABLED"] = "false"
        os.environ["ARBY_ENROLLMENT_V2_ENABLED"] = "false"
        os.environ["ARBY_SETTINGS_RUNTIME_ENABLED"] = "false"
        populate_demo(db)
        from main import app
        import uvicorn
        print("\nVERSIONARY — DISPOSABLE DASHBOARD DEMO", flush=True)
        print("URL: http://127.0.0.1:%s/admin/dashboard" % args.port, flush=True)
        print("Admin bearer token: %s" % admin_token, flush=True)
        print("Demo data: one pending agent; one approved agent with heartbeat and zero updates.", flush=True)
        print("Open the URL on THIS computer. Paste the token, then click Refresh fleet.", flush=True)
        print("Approve the pending agent using its dashboard button. No real agent is contacted.", flush=True)
        print("Press Ctrl+C to stop. The temporary database is deleted on exit.\n", flush=True)
        try:
            uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")
        except KeyboardInterrupt:
            pass
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
