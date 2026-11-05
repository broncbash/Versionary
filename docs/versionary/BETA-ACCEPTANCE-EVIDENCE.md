# Versionary — Controlled Beta Acceptance Evidence

Updated: 2026-11-05
Branch: feature/versionary-agent-rename
Verified baseline: 357c5fa
Full local regression: 1,624 tests; 1 skipped; 0 failures.

## Purpose

Track observed evidence separately from outstanding beta
acceptance. Passing unit and isolated integration tests
does not authorize real-system installation or release.

## Gate 1 — Server installation

Status: ACCEPTANCE PENDING

Existing disposable beta evidence demonstrates an HTTPS
server, agent connectivity, and dashboard functionality.

Still required for the release candidate:
- Confirm clean installation on an authorized disposable VM.
- Confirm HTTPS trust, service startup and restart.
- Record installation and recovery outcomes.

## Gate 2 — Agent installation

Status: ACCEPTANCE PENDING

Observed local evidence:
- Verified 26L distribution available.
- Complete isolated fresh installation succeeds.
- All 13 agent modules installed.
- CLI, CA, configuration and systemd files installed.
- Existing installation is rejected by fresh-only wrapper.
- No enrollment or service activation during installation.

Relevant tests:
- test_versionary_beta_full_fresh_install_77.py
- test_agent_offline_integration.py
- test_beta09_distribution_acceptance.py

Still required:
- Separately authorized real-system beta installation path.
- Fresh-install acceptance on disposable Arch Linux.
- Fresh-install acceptance on disposable Debian 13.
- Service and timer startup, reporting and reboot checks.

Real-system installation is currently disabled.

## Gate 3 — Enrollment and security

Status: IMPLEMENTED; ACCEPTANCE PENDING

Existing tests cover:
- Registration and approval.
- Cryptographic enrollment.
- Credential handling.
- Authenticated heartbeat and reporting.
- Revocation and rejected unauthorized requests.

Relevant tests:
- test_beta_agent_server_journey.py
- test_beta09_end_to_end_acceptance.py
- test_agent_enrollment_crypto.py

Still required:
- Verify complete lifecycle on accepted disposable systems.
- Review administrator credential handling.

## Gate 4 — Dashboard and reporting

Status: IMPLEMENTED; ACCEPTANCE PENDING

Existing tests cover authenticated inventory, reporting,
dashboard behavior and lifecycle interactions.

Still required:
- Observe installed agents reporting on both distributions.
- Verify browser workflows and error handling.
- Confirm no patch installation occurs.

## Gate 5 — Recovery

Status: PARTIAL; ACCEPTANCE PENDING

Existing isolated tests cover installation recovery,
interrupted stages, journal handling and upgrade prototypes.

Known limitation:
The complete offline installer has multiple stages.
It is not globally atomic. Partial installations may
require manual review and cannot be treated as fresh.

Initial controlled beta supports fresh installs only.
In-place upgrades remain deferred.

Still required:
- Document safe manual handling of partial installations.
- Verify recovery behavior on an authorized disposable VM.

## Gate 6 — Packaging and documentation

Status: PARTIAL

Verified 26L distribution exists and is exercised by
the local integration tests.

Still required:
- Final artifact verification and release provenance.
- User-facing fresh-install and recovery instructions.
- Reconcile status, roadmap, handoff and user guide.

## Gate 7 — Final beta acceptance

Status: NOT APPROVED

Requirements:
- All mandatory fresh-install acceptance checks pass.
- No unresolved critical security issues.
- Limitations documented.
- Artifacts validated.
- Explicit user authorization for beta publication.

## Existing disposable beta systems

Historical environment:
- Arch server: 192.168.122.249
- Arch agent: 192.168.122.81
- Debian 13 agent: 192.168.122.34

These systems must not be changed without explicit approval.

Prefer new, disposable clean-install targets for the next
acceptance trial, subject to user approval.

## Next action

Prepare a narrowly scoped fresh-install trial with:
- Target identification and snapshot/recovery plan.
- Exact installation and verification commands.
- Explicit authorization boundary.
- Recorded pass/fail evidence.

Do not enable the real-system installer merely because
the isolated installation passes.

## Standing restrictions

No hosted CI, merge, tag, published release, production
deployment, automatic patching or automatic rebooting.

No changes to CT 102, CT 104 or existing disposable beta
VMs without explicit approval.

Preserve all untracked files, certificates, credentials,
databases, backups and local beta directories.
