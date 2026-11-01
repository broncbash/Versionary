# Versionary — Project Status

Updated: 2026-11-01
Repository: broncbash/arby-patch-command
Development branch: feature/versionary-agent-rename
Last confirmed commit: 80a8217

## Purpose

Versionary is a Linux fleet patch visibility and monitoring platform.

The initial product is observer-only:
- Discover and identify managed agents.
- Collect update inventories.
- Display fleet health and patch availability.
- Support administrator-controlled agent approval and revocation.
- Avoid automatic patch installation, package upgrades, and reboots.

## Current implementation

### Server

- Python FastAPI application.
- SQLite-backed agent registry and report storage.
- Agent registration, approval, revocation, heartbeat, and reporting.
- Ed25519-based enrollment challenge/proof workflow.
- Credential-based agent authentication.
- Administrator dashboard with inventory, filtering, agent approval, and explicitly confirmed irreversible revocation.
- Isolated HTTPS beta tooling and acceptance tests.

### Agent

- Portable Python CLI: versionary_agent_cli.py
- Private local identity and credential storage.
- HTTPS connection configuration with a supplied CA certificate.
- Manual registration, enrollment, heartbeat, and update reporting.
- Arch-family and Debian-family package scanning support.
- No automatic background service installation.

### Portable setup

File: installer/versionary-agent-setup.py

Supported:
- Interactive prompts for missing connection settings.
- Unattended setup with explicit arguments.
- Dry-run validation and preview.
- Private state directory and configuration.
- Refusal to overwrite existing configuration.
- HTTPS-only server origin validation.
- Rejection of CA certificate symlinks.

Not yet supported:
- Distributable agent packaging.
- Automatic certificate retrieval or trust installation.
- Installation or upgrade lifecycle management.
- Service installation or scheduled reporting.
- GUI-driven agent deployment.

## Verification

Latest verified checkpoint (2026-11-01):
- Full local unittest discovery completed with exit status 0.
- Dashboard regression suite: 27 tests passed.
- Dashboard/HTTPS beta route compatibility: 2 tests passed.
- Exact full-suite test count was not captured in the checkpoint summary.
- Previous HTTPS lifecycle and security regression coverage retained.
- Commit 80a8217 pushed to feature/versionary-agent-rename.

A Starlette/httpx deprecation warning remains in the test environment.
It did not fail the verified regression suite.

## Readiness

Development and isolated testing only.

Production approval: NOT GRANTED.
Production deployment: NOT PERMITTED.
Automatic patching: NOT IMPLEMENTED.

The portable setup tool is currently a configuration bootstrap,
not a finished installation package.

## Protected environments

Do not change Proxmox, CT104, CT102, CT103, or other production
homelab systems without explicit user authorization.

Do not silently enable enrollment/reporting feature gates.

## Protected local desktop items

Do not modify, delete, stage, or commit:

- .versionary-local-beta/
- .versionary-timer-preview/
- installer/setup-config.py.pre-batch8
- return-prompt.md

Also preserve .versionary-https-beta/ and any certificates, private
keys, credentials, tokens, or databases it contains.

## Naming

Versionary is the intended professional product name.
The GitHub repository and some internal legacy identifiers still use
arby-patch-command / ARBY naming.

Complete the rename deliberately; do not break compatibility or
rename the repository without explicit approval.


## Current development priorities (2026-11-01)

1. Maintain the verified dashboard lifecycle API compatibility.
2. Implement a read-only coordinated transaction planner.
3. Expand disposable fault-injection and recovery validation.
4. Continue portable installer and certificate-management development.
5. Keep production deployment disabled until explicitly approved.

The disposable beta VM has demonstrated approved agent enrollment,
trusted HTTPS communication, and update reporting. Its reporting timer
remains intentionally disabled. Do not change the VM without approval.

The coordinated rollback design remains a design gate, not an implemented
production-safe rollback mechanism.

## Mission 5B — Release-aware rollback planning

Verified 2026-11-01.

- Added read-only inspection of the active agent release symlink.
- Integrated active-release metadata into the existing rollback planner.
- Preserved the four-asset snapshot format and partial-installation compatibility.
- Added security tests for unsafe release pointers and filesystem layouts.
- Release contents are not authenticated by the inspector.
- Rollback execution remains disabled; `apply_allowed` is false.
- Full repository regression: 1,262 tests, zero failures/errors, one skipped.
- `git diff --check`: passed.
- Production deployment remains unauthorized.
