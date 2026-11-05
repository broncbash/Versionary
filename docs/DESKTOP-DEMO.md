# Patch Command — Desktop Demo

## Purpose

The desktop demo lets developers and evaluators inspect the Patch Command
fleet dashboard without installing agents or connecting to production systems.

This is a local demonstration, not a production deployment.

## Start the demo

From the repository root on the development workstation:

    .venv/bin/python -m uvicorn desktop_demo:app --host 127.0.0.1 --port 8765

Manually enter this URL into the browser address bar:

    http://127.0.0.1:8765/admin/dashboard

The dashboard automatically loads six fictional agents.

Press Ctrl+C in the server terminal to stop the demo.

## Fictional fleet

| Agent | Platform | State | Health | Updates |
|---|---|---|---|---|
| arch-workstation | Arch | Approved | Online | 12 |
| debian-web | Debian | Approved | Online | 4 |
| build-runner | Arch | Approved | Stale | 19 |
| nas-node | Debian | Pending | Pending | Unknown |
| old-test-vm | Arch | Revoked | Revoked | Unknown |
| new-laptop | Arch | Approved | No contact | Unknown |

The demo uses generated timestamps and fixed fictional inventory.
It does not discover devices or query real package managers.

## Available endpoints

- GET /health
- GET /api/v1/admin/agents
- GET /admin/dashboard

The demo does not expose agent registration, approval, revocation,
configuration changes, package installation, or other mutation endpoints.

## Security and limitations

- Bind the demo to 127.0.0.1 only.
- No real administrator token is required.
- The demo's placeholder credential is not a security mechanism.
- Do not expose the demo through a public reverse proxy or tunnel.
- No production database, agent credentials, or homelab services are needed.
- The demo intentionally uses a reduced, read-only application.
- The demo dashboard inherits presentation code from dashboard_ui.py.
- The real dashboard and its authentication remain unchanged.
- The Clear Access control is disabled in the demo.
- Refresh Fleet remains available.

## Tests

Run the focused tests:

    .venv/bin/python -m unittest discover -s tests -p 'test_desktop_demo.py' -v

Run the full offline readiness checks:

    .venv/bin/python installer/local-readiness.py

The readiness process is intended for disposable local testing.
Passing these checks does not authorize production deployment.

## Development boundaries

This demonstration must not:

- Modify CT104, CT102, or other homelab systems.
- Install or activate production agents.
- Change the production authentication model.
- Enable hosted GitHub CI.
- Merge changes into develop or main without approval.

## Known limitations

The demonstration is not a replacement for testing against a real,
authenticated Patch Command server.

The interface displays fictional fleet information. It does not
perform network discovery, live agent communication, or patch operations.

## Enhanced demo controls — October 30, 2026

The desktop demonstration includes additional controls that are
not part of the production dashboard.

### Simulation banner

A prominent SIMULATION MODE banner identifies the dashboard as
a fictional demonstration with no live infrastructure access.

### Health filtering

The Health dropdown filters the currently displayed agent cards:

- All health states
- Online
- Stale
- Pending
- Revoked
- No contact

Health filtering works alongside the existing hostname search,
approval-status filter, and sorting controls.

### Reset filters

Reset filters clears the hostname search, restores the approval
filter to All statuses, restores hostname sorting, and restores
the health filter to All health states.

### Refresh fleet

Refresh fleet requests a new fictional snapshot from the local
demo endpoint. No real agents or production services are contacted.

### Demo information endpoint

GET /demo/about returns basic information about the simulated
environment, including confirmation that mutations are disabled.

### Browser verification

The enhanced interface was manually checked in Brave Origin Nightly
on an Arch Linux development workstation.

The user reported that the automatic fleet population, simulation
banner, health filters, reset control, and refresh functionality
appeared to work correctly.

### Implementation boundary

The enhancements are applied to the demo's rendered HTML.
The production dashboard source and authentication behavior
remain unchanged.
