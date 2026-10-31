# Release readiness and safe rollout checklist

**Status:** Development only. This is a review checklist, not an installation
or deployment authorization.

## Verified in GitHub CI

- The agent package is generated from tracked sources before tests.
- Python modules compile, the shell installer passes `bash -n`, and the
  unittest suite runs against multiple Python versions.
- Agent API registration/reporting can optionally use the validated,
  fail-closed settings bridge; no opt-in means legacy environment-only behavior.
- Settings UI/API/CLI runtime status is read-only and administrator-protected.
- V2 enrollment router is separate and not included in `main.py`.

## Release blockers

1. **Portability:** `main.py` still has hard-coded homelab addresses in
   legacy SSH update endpoints. Replace these with user-configurable inventory
   and migration tests; do not silently remove existing CT104 functionality.
2. **Enrollment architecture:** reconcile V1 legacy agent routes and the
   isolated V2 cryptographic enrollment workflow; document approval, identity,
   revocation, and credential migration before enabling network enrollment.
3. **Transport security:** demonstrate a real TLS handshake and agent CA trust
   onboarding. Validate hostname/IP SANs, renewal, certificate import, and
   rollback without exposing private keys.
4. **Production installer:** `--install` is intentionally disabled. Design
   idempotent server and agent installers, safe upgrades, systemd integration,
   backups, and uninstall/rollback.
5. **GUI/CLI parity:** certificate management and practical server/agent
   administration still need equivalent, authenticated web and CLI workflows.
6. **Deployment safety:** test a clean install and an upgrade from a backed-up
   CT104 copy before any change to the live service.
7. **Product identity:** choose a standalone name before public packaging;
   retain existing ARBY identifiers until the migration is designed.

## Non-negotiable rollout constraints

- Never enable unattended patch installation or automatic reboots by default.
- Never deploy to CT104 or CT102, merge the draft PR, rotate live TLS material,
  or enable V2 enrollment without explicit owner approval.
- Never store CA private keys, bearer tokens, or agent credentials in Git.
- Preserve the running observer-only service and legacy update visibility until
  replacement paths have been tested and approved.

## Recommended next development milestone

Implement a portable **inventory configuration** for the legacy update scanner
endpoints with read-only validation, explicit fallback behavior, and isolated
tests. Keep the live deployment unchanged. After that, work on V2 enrollment
integration and a reversible server installer.


## Transactional release trust state — development milestone

At commit 4ceb26a, the development branch includes authenticated
monotonic policy updates, transactional SQLite state, a development
administrative CLI, and adversarial filesystem and recovery tests.

The verified milestone completed 1,106 tests, one skipped, zero failures.

This milestone does not authorize production deployment.

### Remaining trust-state blockers

- Authenticated backup and recovery
- Rollback and conflicting-policy rejection
- Independent freshness mechanism for database replacement threats
- Remaining filesystem-race review
- Administrative GUI/CLI parity
- Operator recovery and audit procedures

See docs/TRUST-STATE-OPERATIONS.md.

Documentation must be updated at every substantial milestone.


## Phase VI-B — Development snapshot export

A development-only trust-state export CLI and snapshot validation
tests have been added.

Exports are exclusive, owner-only files in private directories.
The export is captured from a SQLite read transaction.

Export integrity checks are not signatures and cannot establish
freshness or prevent privileged snapshot rollback.

Authenticated recovery, independent freshness protection, and
production integration remain release blockers.
