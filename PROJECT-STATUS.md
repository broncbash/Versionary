# Patch Command — Comprehensive Project Handoff

**Checkpoint date:** 2026-10-29  
**Repository:** `broncbash/arby-patch-command` (private)  
**Development branch:** `feature/runtime-visibility`  
**Integration target:** `develop` (draft PR #1); `main` remains baseline  
**Deployment status:** experimental development; **no production rollout authorized**

> **Provenance:** This is a total AI slop project: predominantly AI-generated code, tests and documentation, directed and checked by a human operator. Passing automated tests does not constitute an independent security audit or production endorsement.

## Mandatory handoff procedure

1. Inspect the **actual remote branch head, tree, and relevant source** before editing. This document is a snapshot, not authority over later commits.
2. Read `README.md`, `docs/USER-MANUAL.md`, and the relevant technical docs.
3. Develop substantial coordinated batches directly on the feature branch; avoid excessive interactive checkpoints.
4. Commit changes to the feature branch; **do not merge, deploy, restart services, or enable network gates without approval**.
5. Give one local copy/paste verification command and wait for the operator's actual results. Do not claim tests passed if only code was committed.
6. Update this handoff and manual when behavior changes.

## Current verified checkpoint

The operator reported the following from their Arch Linux desktop on 2026-10-29:

```
Ran 622 tests in 7.759s
OK
[Patch Command] PASS
[Patch Command] Running isolated beta HTTPS acceptance...
"status": "passed"
"tls_protocol_check": "passed"
"production_installed": false
"systemd_started": false
"agent_enrolled": false
"external_network_requests_made": false
```

This verified the code through commit `3d9dc53` on `feature/runtime-visibility`, **not** later documentation or code changes. The isolated shell installer smoke test was changed to invoke the installed agent CLI help rather than depend on live Arch package mirrors. The optional real scan remains separately testable.

**Local verification command:**

```bash
cd ~/Projects/arby-patch-command && git pull --ff-only && bash installer/local-check.sh --protocol-check
```

Full unittest log defaults to `/tmp/arby-tests.log`. Hosted CI is manual/checkpoint-oriented; avoid triggering GitHub Actions casually.

## Architecture and implementation

**Server:** FastAPI `main.py` with health endpoint, legacy local/SSH update scanner endpoints, agent-related routers, admin inventory and browser UI. Legacy endpoints are still present while the agent architecture matures.

**Persistence:** SQLite registry in `agent_registry.py` stores agents, states, reports, and credential hashes. Existing deployment uses a legacy data path; tests use disposable databases. Never overwrite a live database or copy secrets into Git.

**Agent:** Python package under `agent/`; identity, credential handling, registration/enrollment, heartbeat, scan and reporting modules. Targets Arch and Debian. Ed25519 challenge/response and trusted TLS are exercised in isolated protocol tests.

**Administrator surface:** `admin_agents_api.py` exposes read-only `/api/v1/admin/agents`, requiring admin auth. `dashboard_ui.py` provides `/admin/dashboard`, with online/attention counts, update totals, agent health, search/filter/sort. `settings_ui.py` provides `/admin/settings`, with staged settings and runtime visibility. Tokens are entered for API requests rather than intentionally persisted by the page.

**Health classification:** approved agents with a valid recent heartbeat (within 30 minutes) are online; stale/no-contact/unknown cases are distinct. Pending and revoked states are not reported as online. Invalid or future timestamps must not be treated as healthy.

**Settings:** `server_settings.py`, `server_settings_api.py`, `runtime_configuration.py`, `runtime_status_api.py` and installer CLI tools provide validation, staged persistence and fail-closed visibility. Settings alone never grant production activation. Legacy environment gates remain part of compatibility and must not be bypassed.

**Certificates:** `certificate_management.py`, `certificate_renewal.py`, `installer/manage-certificates.py` and generation helpers provide offline certificate handling. They do not imply live TLS termination, automatic CA rotation, or proxy reload.

**Installation:** `installer/build-agent-package.py`, `validate-package.py`, `install-files.py`, `install-ca.py`, `setup-config.py`, `install-systemd.py`, `stage-beta.py`, `audit-test-install.py`, `agent-preflight.py`, `deployment-readiness.py`, `beta-selftest.py`, and `beta-evaluate.py` support packaging, secure filesystem operations, inert staging and disposable verification. `installer/install-agent.sh --install` remains **disabled**.

**Security design:** restrictive private directories, non-following file operations, validated archive contents, atomic release and integrity mechanisms, staged certificate validation, explicit agent approval and credential revocation. These are engineering intentions with automated tests, **not** an independent security certification.

## Homelab deployment boundary

- Proxmox VE 9 mini PC; current live service on **CT104** (Arch Linux).
- **CT102** (Arch Linux) runs monitoring and has legacy integration.
- CT100 Debian DNS; CT101 Debian Docker; CT103 Arch Tailscale subnet router.
- The new feature branch is **not** presumed installed on any of these.
- **Never modify CT104 or CT102 without explicit operator approval.** Do not silently change other live containers either.
- No unattended package upgrades, automatic reboots, unsolicited agent enrollment, or automatic service restarts.

## Product and naming decisions

The public-facing product name is **Patch Command**, with restrained professional UI styling. Do not reintroduce the older branding or aesthetic terminology in visible UI, messages, or new code. Some old internal identifiers, paths, service unit names, environment variables and persisted settings values must remain until a deliberate compatibility migration is designed and tested. Use neutral language in new code where feasible.

The repository must **clearly disclose AI authorship**. The README includes the user's exact requested wording, alongside an explicit caution that independent review is required. Avoid pretending the project has been professionally audited.

## Development milestones completed

- Registry, agent approval/revocation, token/credential lifecycle, heartbeat and report storage.
- Feature-gated agent API and staged settings/runtime-status interfaces.
- Offline certificate import/inspection/renewal foundations.
- Package builder and archive validation, private-state-safe installer components, atomic release handling and filesystem hardening tests.
- Isolated beta staging, repeated-installation integrity audit, and disposable loopback TLS enrollment/reporting acceptance.
- Authenticated read-only agent inventory and professional fleet dashboard, including search/filter/sort and conservative health indicators.
- Offline beta evaluation wrapper and user-reported 622-test checkpoint.
- Fixed flaky shell-installation regression that depended on external package repository availability.

Historical docs such as `BUILD3-NOTES.md` describe earlier milestones; **do not treat their old branch names or outstanding-task lists as current**.

## Outstanding work — prioritized

1. **Controlled beta installer:** implement a reviewed, explicit installation transaction, dependency preflight, durable backup/rollback, idempotent reinstall and safe service lifecycle. Do not simply enable the current `--install` switch.
2. **Approved end-to-end enrollment:** clean disposable Arch/Debian container trial with HTTPS trust, manual approval, authenticated heartbeat/reporting, and revocation, all with clear audit evidence.
3. **Production-safe server setup:** supported TLS termination, configuration/apply semantics, admin authentication hardening, secrets management, migration and rollback.
4. **Fleet operations:** safe agent discovery/onboarding design, approval UI, richer operational failure states and documentation.
5. **Compatibility cleanup:** staged migration away from legacy identifiers and paths, with backward-compatible upgrade tests.
6. **Independent security review:** threat model, privilege analysis, filesystem/SQLite race conditions, token exposure, CA trust lifecycle, authorization boundaries, dependency and supply-chain review.
7. **Release readiness:** clean installation on supported distributions, upgrade/uninstall procedures, recovery testing, reproducible packaging and user documentation.

## Next development session

Inspect `feature/runtime-visibility` first. The next intended engineering milestone is a **usable beta installation workflow** with preflight and rollback safeguards, developed and tested **without** touching live systems. Work in substantial batches; provide one local regression command. Do not assume passing disposable tests means the operator approved deployment.

## Reference index

- `README.md` — overview, AI provenance and project entry point
- `docs/USER-MANUAL.md` — current operator manual
- `BETA-EVALUATION.md` — disposable beta workflow
- `docs/DEPLOYMENT-BETA-GATE.md` — explicit production blockers
- `docs/RUNTIME-VISIBILITY.md` — runtime gate behavior
- `docs/AGENT-INSTALL-PREFLIGHT.md` and `docs/AGENT-INSTALL-AUDIT.md` — installation checks
- `docs/RELEASE-READINESS.md` — release-related controls
- `BUILD3-NOTES.md` — historical certificate milestone notes

**Last rule:** GitHub commits are development authorization only. Never equate them with authorization to change live infrastructure.
