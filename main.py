from versionary_agent_distribution import router as distribution_router
from agent_reporting_api import router as reporting_router
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from scanner_inventory import target, InventoryError
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

# Existing v2 enrollment protocol, disabled by default behind its feature gate.
from enrollment_v2_api import router as enrollment_v2_router
app.include_router(enrollment_v2_router)

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
    try:
        config = target("proxmox")
    except InventoryError:
        raise HTTPException(status_code=503, detail="Scanner inventory unavailable")
    return scan_apt_updates(node=config["node"], host=config["host"])

@app.get("/api/v1/updates/dns-guard")
def dns_guard_updates():
    try:
        config = target("dns-guard")
    except InventoryError:
        raise HTTPException(status_code=503, detail="Scanner inventory unavailable")
    return scan_apt_updates(node=config["node"], host=config["host"])

@app.get("/api/v1/updates/docker-nodes")
def docker_nodes_updates():
    try:
        config = target("docker-nodes")
    except InventoryError:
        raise HTTPException(status_code=503, detail="Scanner inventory unavailable")
    return scan_apt_updates(node=config["node"], host=config["host"])

@app.get("/api/v1/updates/monitoring")
def monitoring_updates():
    try:
        config = target("monitoring")
    except InventoryError:
        raise HTTPException(status_code=503, detail="Scanner inventory unavailable")
    return scan_remote_arch_updates(node=config["node"], host=config["host"])

@app.get("/api/v1/updates/tailscale")
def tailscale_updates():
    try:
        config = target("tailscale")
    except InventoryError:
        raise HTTPException(status_code=503, detail="Scanner inventory unavailable")
    return scan_remote_arch_updates(node=config["node"], host=config["host"])

app.include_router(reporting_router)

# Admin-only staging endpoints; settings are not automatically applied.
from server_settings_api import router as settings_router
app.include_router(settings_router)

# Self-contained staging UI; API access still requires an admin bearer token.
from settings_ui import router as settings_ui_router
app.include_router(settings_ui_router)

# Authenticated, read-only beta agent inventory (no feature gates changed).
from admin_agents_api import router as admin_agents_router
app.include_router(admin_agents_router)

# Read-only cyberpunk agent fleet dashboard.
from dashboard_ui import router as dashboard_router
app.include_router(dashboard_router)

app.include_router(distribution_router)
