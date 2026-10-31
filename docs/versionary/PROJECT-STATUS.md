# Versionary — Project Status

Updated: 2026-10-31
Repository: broncbash/arby-patch-command
Development branch: feature/versionary-agent-rename
Last confirmed commit: 681e8b4

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
- Read-only administrator dashboard prototype.
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

Last confirmed selected regression:
- 68 tests passing.
- Python compilation successful.
- SQLite connection leak warnings addressed.
- Real disposable HTTPS agent lifecycle covered.

The 68-test result refers to the selected agent/HTTPS regression suite,
not necessarily every test in the repository.

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
