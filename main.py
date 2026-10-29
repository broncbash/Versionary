from agent_reporting_api import router as reporting_router
from datetime import datetime, timezone

from fastapi import FastAPI
from agent_api import router as agent_router
from agent_enrollment_api import router as enrollment_router
from scanner import scan_arch_updates
from remote_scanner import scan_proxmox_updates, scan_apt_updates
from arch_remote_scanner import scan_arch_updates as scan_remote_arch_updates

app = FastAPI(
    title="ARBY PATCH COMMAND",
    description="Arby Homelab Patch Management Platform",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
)

app.include_router(agent_router)
app.include_router(enrollment_router)

@app.get("/health")
def health():
    return {
        "service": "ARBY PATCH COMMAND",
        "status": "online",
        "version": "0.1.0",
        "mode": "observer",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/v1/updates/local")
def local_updates():
    return scan_arch_updates()

@app.get("/api/v1/updates/proxmox")
def proxmox_updates():
    return scan_proxmox_updates()

@app.get("/api/v1/updates/dns-guard")
def dns_guard_updates():
    return scan_apt_updates(
        node="DNS GUARD",
        host="192.168.86.10",
    )

@app.get("/api/v1/updates/docker-nodes")
def docker_nodes_updates():
    return scan_apt_updates(
        node="DOCKER NODES",
        host="192.168.86.12",
    )

@app.get("/api/v1/updates/monitoring")
def monitoring_updates():
    return scan_remote_arch_updates(
        node="MONITORING",
        host="192.168.86.13",
    )

@app.get("/api/v1/updates/tailscale")
def tailscale_updates():
    return scan_remote_arch_updates(
        node="TAILSCALE",
        host="192.168.86.14",
    )

app.include_router(reporting_router)

# Admin-only staging endpoints; settings are not automatically applied.
from server_settings_api import router as settings_router
app.include_router(settings_router)
