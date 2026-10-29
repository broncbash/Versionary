# Patch Command — User Manual

**Edition:** 2026-10-29 development checkpoint  
**Audience:** operator/developer evaluating the current repository  
**Status:** experimental; **not** a production installation guide

## 1. Purpose and boundaries

Patch Command helps operators inspect Linux package-update availability and the state of reporting agents. It is designed around **observer-only** operation: view updates, contact status, and reports; do not silently apply packages or reboot hosts.

The repository contains both legacy SSH-based scanners and a newer agent architecture. These are not interchangeable deployment modes. Existing homelab installations may still run older code; the feature branch is **not** evidence that a live server has been upgraded.

## 2. What is available

| Capability | Current state |
| --- | --- |
| FastAPI health endpoint `GET /health` | Implemented |
| Legacy local/remote update endpoints | Implemented; depend on local scanner/SSH configuration |
| Agent registry, approval, revocation, credential lifecycle | Implemented components with automated tests |
| Agent heartbeat and update reporting | Implemented components; activation gated |
| `GET /api/v1/admin/agents` | Authenticated, read-only inventory |
| `/admin/dashboard` | Read-only fleet view; search, filter, sort, health |
| `/admin/settings` | Staged settings and runtime-gate visibility |
| Agent package build and validation | Implemented |
| Isolated agent installation and audit | Implemented |
| Disposable loopback HTTPS enrollment/reporting test | Implemented |
| Production agent `--install` | **Disabled** |
| Automatic network discovery and unattended patching | **Not delivered** |

The dashboard's health assessment uses a conservative heartbeat age threshold (30 minutes for an approved agent). Missing, stale, malformed or future timestamps are not proof of a healthy connection. Scan errors are distinct from zero available updates.

## 3. Local prerequisites

For the documented local regression workflow, use a checkout with a Python virtual environment at `.venv` and project dependencies installed. The user's verified development environment is an Arch Linux desktop running Python 3.14. Agent candidates target Arch Linux and Debian, with Python 3.11+, systemd, the appropriate read-only package scanner (`checkupdates` or `apt`), cryptography support, and a trusted HTTPS server CA.

The agent archive is generated locally; do not assume `installer/dist/` exists in a fresh checkout.

## 4. Local verification (recommended)

```bash
bash installer/local-check.sh --protocol-check
```

This command:
1. Builds the agent archive.
2. Runs all `tests/test_*.py` via Python unittest and records full output in `/tmp/arby-tests.log`.
3. If the suite passes, runs disposable isolated HTTPS acceptance.

Override the log path with `PATCH_COMMAND_TEST_LOG=/path/to/log` (the older `ARBY_TEST_LOG` override remains supported).

**Last reported result:** 622 tests passed and HTTPS acceptance passed on 2026-10-29. Test totals are historical checkpoints, not guaranteed for new revisions.

The isolated installer smoke test checks that the installed agent CLI starts **without requiring live package repositories**. A real package scan is a separate, optional check; `checkupdates` can fail when mirrors are unreachable, which is not the same as installation failure.

## 5. Beta evaluation without deployment

```bash
.venv/bin/python installer/beta-evaluate.py --protocol-check
```

This checks package creation, isolated staging/re-staging, integrity, and a disposable TLS protocol journey. A passing result may report local loopback network requests; it does **not** contact an external server, enroll a real agent, install production files, or start systemd services.

An isolated shell installer test is also available after package creation:

```bash
bash installer/install-agent.sh --test-install
```

It uses a temporary root and removes it afterward. The `--install` flag intentionally refuses production deployment.

For retained, **inert** beta staging in a disposable test environment, consult [the deployment gate](DEPLOYMENT-BETA-GATE.md). Staging is not a transactional production installer.

## 6. Web UI and API

When running a suitably configured **development** server:

- `/admin/dashboard`: agent fleet summary, per-agent health and update counts, search/filter/sort.
- `/admin/settings`: staged configuration, runtime status, and agent inventory access.
- `GET /api/v1/admin/agents`: authenticated JSON inventory.
- `GET /api/v1/admin/settings/runtime-status`: authenticated read-only effective-gate report.
- `GET /health`: basic server health response.

Administrator APIs require the configured bearer-token authentication. Browser pages accept a token in memory for API calls; do not paste a production token into an untrusted page. The dashboard does not grant agent approval or enable reporting by itself.

The Settings page saves **staged** values; `applied: false` must not be interpreted as an active runtime configuration. Runtime feature gates default closed, and existing environment-based controls still matter. Read [runtime visibility](RUNTIME-VISIBILITY.md) before interpreting these settings.

## 7. Agent lifecycle — conceptual workflow, not a live rollout procedure

The intended controlled sequence is: build and validate package → verify prerequisites and trusted CA → stage in a disposable environment → register agent against an explicitly enabled test server → administrator approves the pending agent → agent completes credential enrollment → authenticated heartbeat and scan reporting → revoke credential when decommissioning.

The repository tests much of this sequence over temporary in-process and loopback HTTPS servers. **Do not attempt it against live containers merely because these tests pass.** A reviewed production installer, explicit authorization, safe certificate handling, and rollback are outstanding gates.

## 8. Read-only readiness tools

`installer/agent-preflight.py` checks agent prerequisites and configuration. `installer/deployment-readiness.py` produces a JSON report distinguishing isolated-test readiness from production readiness. Production readiness is deliberately false. See [deployment gate](DEPLOYMENT-BETA-GATE.md) for supported arguments and interpretation.

Certificate tools support validation, inspection, offline import and renewal scenarios. These tools do **not** automatically update a TLS proxy, reload services, rotate deployed trust, or safely replace a live certificate. Refer to `BUILD3-NOTES.md` and the certificate-management source before use.

## 9. Troubleshooting

**Test suite fails:** inspect the full log at `/tmp/arby-tests.log` (or configured override), starting with `FAIL:` or `ERROR:`. Do not assume the last console lines identify the failing test.

**Scanner reports “Cannot fetch updates”:** check the host's package mirror/network state. Do not treat this as a successful scan with zero updates. Offline installation tests should still pass.

**Agent missing from dashboard:** confirm it exists in the expected registry database, its approval state, effective feature gates, and whether any heartbeat/report has actually been received. A staged or disabled agent does not imply active communication.

**Settings show enabled but runtime is disabled:** staged settings alone do not activate the server; inspect the effective runtime status and required gates.

**TLS errors:** confirm the URL hostname/IP matches the certificate SAN and that the client trusts the correct CA. Do not bypass certificate verification to force a test to pass.

## 10. Known limitations and safety

- No approved production installer or supported automated rollback workflow yet.
- No approved deployment of the new agent stack to live infrastructure.
- No unattended upgrades, reboots, or automatic LAN agent discovery.
- A passing disposable TLS test does not prove a real network deployment is safe.
- Legacy internal service names and filesystem paths remain for compatibility.
- This code is AI-authored and requires independent review, especially around credentials, authentication, filesystem security and update-scanning privileges.

For future development context, read [the current handoff](../PROJECT-STATUS.md). For production acceptance requirements, read [the deployment gate](DEPLOYMENT-BETA-GATE.md).
