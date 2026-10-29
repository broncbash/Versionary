# ARBY PATCH COMMAND — Project status and handoff

**Updated:** 2026-10-29  
**Repository:** `broncbash/arby-patch-command` (private)  
**Active branch:** `feature/settings-certificates`  
**Verified remote head at time of writing:** `bac34fcacc1987ff86a6f7ad41564ca70932f75c`  
**Status:** Development only; **not approved for production deployment**.

## Read this first

This document is the durable handoff for future development sessions. **Inspect the repository and branch head before modifying code.** Treat the code and current test results as authoritative over older chat summaries or checkpoint archives. Do not assume unpushed work exists in GitHub.

The user prefers **substantial coordinated batches**, few interruptions, direct GitHub updates, and clear short reports. Do not ask the user to say “go” after every checkpoint. Make safe development changes on a feature branch, run tests, and prepare a pull request. Ask before any production deployment or destructive action. The user prefers **Arch Linux**, **nvim** when editing manually, and complete copy/paste commands rather than piecemeal edits when terminal action is necessary.

## Environment and workflow

- Development workstation: Arch Linux desktop; user previously verified Python **3.14.8** and the project venv.
- Source of truth: private GitHub repository, with `main` as stable baseline, `develop` for integration, and feature branches for work. Current branch: `feature/settings-certificates`.
- Production server: Proxmox **CT 104**, Arch Linux, running the existing ARBY PATCH COMMAND service. **Do not change CT 104 without explicit user approval.**
- Monitoring: **CT 102** runs monitoring and a legacy V1 agent. **Do not change CT 102 without explicit user approval.**
- Production behavior is observer-only: no unattended package upgrades, automatic reboots, or automatic deployment.
- V2 enrollment/reporting and new TLS settings must remain isolated from the production service until explicitly reviewed and approved.
- Preferred delivery: commit and push tested changes to the feature branch, then open a PR to `develop`; do not merge or deploy automatically. Before any production rollout, plan backup, migration, verification and rollback.

## Confirmed GitHub progress

The repository currently contains Build 2's settings foundation and the following Build 3 feature commits on `feature/settings-certificates`:

| Commit | Confirmed milestone | Desktop tests reported |
| --- | --- | --- |
| `a3f2e2f` | Certificate import/validation and staging Settings UI | 444 passed |
| `26b14a1` | Certificate inspection and expiration warnings | 451 passed |
| `22ed10a` | Offline server-leaf certificate renewal | 458 passed |
| `2c085b9` | Read-only installer settings preflight | 465 passed |
| `bac34fc` | Fail-closed runtime configuration bridge | 471 passed |

**Important synchronization note:** Two later archives were offered in chat: a runtime-status UI/API integration (476 tests claimed in the assistant's isolated environment) and settings hardening (481 tests claimed). **Neither has been confirmed applied or pushed to GitHub.** They must not be described as present in the repository. Inspect the GitHub files before reimplementing or integrating those ideas. All numbered test counts above are user-reported desktop results except where explicitly labeled otherwise; rerun tests for any new change.

## Existing functionality (staged, not live)

- `server_settings.py`: schema validation and private atomic JSON settings persistence.
- `server_settings_api.py`: administrator-authenticated settings GET/PATCH endpoints; API responses explicitly indicate `applied: false`.
- `settings_ui.py`: preliminary cyberpunk-themed Settings page with in-memory bearer-token entry; staging only.
- `installer/settings-cli.py`: settings read/write CLI.
- `installer/generate-certificates.py`: local certificate generation foundation.
- `certificate_management.py` and `installer/manage-certificates.py`: certificate/key validation, non-overwriting import, and certificate inspection.
- `certificate_renewal.py`: offline server certificate/key renewal using an existing CA; no live proxy reload or trust rotation.
- `installer/settings-preflight.py`: read-only configuration readiness checks.
- `runtime_configuration.py` and `installer/runtime-status.py`: fail-closed effective flag evaluation and read-only reporting; **not connected to production routers**.
- Existing agent registry, approval/revocation, credential authentication, heartbeats, scan reporting and legacy SSH scanner components remain in the repository; confirm precise routing and integration in code.

See `BUILD3-NOTES.md` and `README-PORTABILITY.md` for command examples and limitations. Those documents contain older checkpoint wording; do not interpret every older “not implemented” statement as current without checking source.

## Product requirements and decisions

1. **Portable product** for other users, not tied to ARBY hostnames, IPs, CA fingerprints, or the current homelab. Avoid hard-coded deployment assumptions.
2. **Friendly interactive installer** and **scriptable noninteractive CLI** for both server and agents, with equivalent administration capabilities where practical.
3. **Web GUI Settings** for server and agent configuration, with equivalent CLI options. Changes should be validated, authorized, auditable, and have safe apply/rollback semantics.
4. **TLS certificate management:** support importing user-supplied certificate/private key and easy generation/management for nonexperts; validate certificate/key match and hostname/IP SAN; securely distribute CA trust to agents; support renewal and eventual CA rotation without silent trust changes. Never commit keys or secrets.
5. **Secure agent lifecycle:** registration, explicit approval, credential issuance/revocation, authenticated reporting, and eventual easy discovery/onboarding. Do not expose V2 enrollment in production by default.
6. **Observer-only patch dashboard** initially; no automatic updates or reboots.
7. **Appearance:** cyberpunk/dark-glass UI is preferred, with user-configurable appearance.
8. **Future branding:** rename ARBY PATCH COMMAND to a professional standalone product name **before packaging/release**, but **do not rename prematurely**.

## Outstanding engineering work (not yet verified complete)

- Connect validated settings to the actual server lifecycle and routing, preserving fail-closed behavior and production V2 isolation.
- Finish Settings GUI and CLI parity; secure certificate upload/generation/inspection/renewal workflows with explicit apply and rollback.
- Implement safe TLS termination integration, CA trust enrollment and renewal/rotation policy.
- Finish server and agent installers, service units, portable configuration and migration handling.
- Add end-to-end tests for TLS handshakes, agent enrollment/approval/reporting, certificate trust and failure cases.
- Audit auth, file permissions, atomic writes, certificate handling, logging and secrets.
- Add CI to run tests on supported Python versions; test on user's Arch desktop before release.
- Plan staged deployment with backups, health checks and rollback; **never touch CT 104 or CT 102 without approval**.

## Recommended next action

Work directly against `feature/settings-certificates` through the connected GitHub integration. Review the current implementation, then develop the next **coordinated** installer/configuration integration batch, run tests, push to the feature branch, and open a PR to `develop` for review. Keep `main` stable. Update this handoff document after meaningful milestones and note exact commit hashes and test environments.

**Security boundary:** Source-control changes are authorized development work; they are **not** permission to deploy, enable agent enrollment/reporting, rotate live certificates, or change any production host.
