"""Local-only Patch Command dashboard demonstration.

All agents are fictional. No production database, credentials, or
network discovery are used.
"""

from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from dashboard_ui import PAGE

app = FastAPI(
    title="Patch Command Desktop Demo",
    docs_url=None,
    redoc_url=None,
)

FLEET = (
    ("arch-workstation", "arch", "approved", "online", 12),
    ("debian-web", "debian", "approved", "online", 4),
    ("build-runner", "arch", "approved", "stale", 19),
    ("nas-node", "debian", "pending", "pending", None),
    ("old-test-vm", "arch", "revoked", "revoked", None),
    ("new-laptop", "arch", "approved", "no_contact", None),
)


def sample_fleet(now=None):
    """Build a fresh, deterministic-shape fictional fleet."""
    if now is None:
        now = datetime.now(timezone.utc)

    agents = []

    for index, (hostname, platform, status, health, count) in enumerate(
        FLEET, start=1
    ):
        if health == "online":
            last_seen = (now - timedelta(minutes=5)).isoformat()
        elif health == "stale":
            last_seen = (now - timedelta(hours=2)).isoformat()
        else:
            last_seen = None

        agents.append(
            {
                "id": index,
                "hostname": hostname,
                "platform": platform,
                "status": status,
                "health": health,
                "registered_at": (now - timedelta(days=3)).isoformat(),
                "last_seen": last_seen,
                "scan_at": last_seen if count is not None else None,
                "scan_status": "success" if count is not None else None,
                "updates": count,
            }
        )

    return {"agents": agents, "count": len(agents)}


@app.get("/health")
def health():
    return {
        "status": "online",
        "mode": "simulated-desktop-demo",
        "production": False,
    }


@app.get("/api/v1/admin/agents")
def agents():
    return sample_fleet()


@app.get("/admin/dashboard", response_class=HTMLResponse)
def dashboard():
    page = PAGE

    # The real dashboard remains unchanged. Only this served copy
    # receives demo-specific adjustments.
    page = page.replace(
        "let credential='';",
        "let credential='demo-only';",
    )

    page = page.replace(
        "Enter an admin token to load the fleet.",
        "SIMULATED DATA - no real agents or authentication.",
    )

    page = page.replace(
        'placeholder="Admin bearer token (memory only)"',
        'placeholder="Demo mode - no token required" disabled',
    )

    page = page.replace(
        '<a href="/admin/settings">Settings</a>',
        '<span>DESKTOP DEMO - NOT LIVE</span>',
    )

    # Hide the real authentication controls in the demo.
    # Keep the original dashboard's refresh mechanism.
    page = page.replace(
        '<button id="clear" type="button">Clear access</button>',
        '<button id="clear" type="button" disabled hidden>'
        'Demo mode</button>',
    )

    # The original dashboard attaches its event handlers before this
    # line executes, so the automatic refresh works immediately.
    page = page.replace(
        "</script></body>",
        "document.getElementById('refresh').click();"
        "</script></body>",
    )

    return HTMLResponse(
        page,
        headers={
            "Cache-Control": "no-store",
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
            "Content-Security-Policy": (
                "default-src 'none'; "
                "script-src 'unsafe-inline'; "
                "style-src 'unsafe-inline'; "
                "connect-src 'self'; "
                "form-action 'none'; "
                "base-uri 'none'; "
                "frame-ancestors 'none'"
            ),
        },
    )
