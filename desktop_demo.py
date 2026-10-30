"""Local-only Patch Command dashboard demonstration.

All agents are fictional. No production database, credentials, or
network discovery are used.
"""

from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from dashboard_ui import PAGE

app = FastAPI(
    title="Versionary Desktop Demo",
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
                "distro_id": platform,
                "distro_name": {"arch":"Arch Linux", "debian":"Debian"}.get(platform,"Linux"),
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

    # Attach fictional health states to cards as they are rendered.
    # This modification applies only to the demo's HTML copy.
    original = "const card=node('article','', 'agent');"
    replacement = (
        "const card=node('article','', 'agent');"
        "card.dataset.health=a.health;"
    )
    if original not in page:
        raise RuntimeError("Dashboard agent-card marker not found")
    page = page.replace(original, replacement, 1)

    page = enhance_demo_page(page)

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


def enhance_demo_page(page):
    """Apply demo-only enhancements to the rendered dashboard."""
    marker = '<div class="grid" id="fleet"'
    if marker not in page:
        raise ValueError("Dashboard fleet marker not found")

    controls = (
        '<div id="demo-tools" class="filters" '
        'aria-label="Demo fleet controls">'
        '<label for="demo-health">Health</label>'
        '<select id="demo-health" aria-label="Filter by health">'
        '<option value="all">All health states</option>'
        '<option value="online">Online</option>'
        '<option value="stale">Stale</option>'
        '<option value="pending">Pending</option>'
        '<option value="revoked">Revoked</option>'
        '<option value="no_contact">No contact</option>'
        '</select>'
        '<button id="demo-reset" type="button">'
        'Reset filters</button>'
        '</div>'
    )
    page = page.replace(marker, controls + marker, 1)

    styles = """
<style>
#demo-banner {
  border: 1px solid #38bdf8;
  background: rgba(14,165,233,.12);
  border-radius: 12px;
  padding: 14px 18px;
  margin: 18px 0;
  color: #bae6fd;
}
#demo-tools { margin: 12px 0 18px; }
#demo-tools label { align-self: center; }
#demo-tools button { cursor: pointer; }
.agent[hidden] { display: none; }
</style>
"""
    page = page.replace("</head>", styles + "</head>", 1)

    banner = (
        '<aside id="demo-banner" role="note">'
        '<strong>SIMULATION MODE</strong> — '
        'Six fictional agents. No live systems, '
        'credentials, or patch operations.'
        '</aside>'
    )
    page = page.replace("<main>", "<main>" + banner, 1)

    script = """
<script>
(function () {
  'use strict';

  const health = document.getElementById('demo-health');
  const reset = document.getElementById('demo-reset');
  const fleet = document.getElementById('fleet');
  const results = document.getElementById('results');

  function applyHealthFilter() {
    const selected = health.value;
    const cards = Array.from(fleet.querySelectorAll('.agent'));
    let visible = 0;

    for (const card of cards) {
      const state = card.dataset.health || 'unknown';

      card.hidden = selected !== 'all' && state !== selected;
      if (!card.hidden) visible++;
    }

    if (selected !== 'all') {
      results.textContent =
        'Showing ' + visible + ' matching health filter';
    }
  }

  health.addEventListener('change', applyHealthFilter);

  reset.addEventListener('click', function () {
    document.getElementById('search').value = '';
    document.getElementById('status-filter').value = 'all';
    document.getElementById('sort').value = 'name';
    health.value = 'all';
    document.getElementById('search').dispatchEvent(
      new Event('input')
    );
  });

  const observer = new MutationObserver(applyHealthFilter);
  observer.observe(fleet, { childList: true });

  // Only child-list changes trigger this observer.
  // Updating the hidden property does not trigger another callback.
})();
</script>
"""
    page = page.replace("</body>", script + "</body>", 1)
    return page


_original_dashboard = dashboard


@app.get("/demo/about")
def demo_about():
    return {
        "mode": "simulation",
        "agents": len(FLEET),
        "production": False,
        "mutations_enabled": False,
    }
