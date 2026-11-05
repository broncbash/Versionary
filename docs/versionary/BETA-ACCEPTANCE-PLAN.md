# Versionary — Controlled Beta Acceptance Plan

Date: 2026-11-04
Baseline commit: acad19b
Local regression: 1,590 tests, one skipped, zero failures.

## Objective

Deliver a usable, controlled beta of Versionary with
repeatable installation, secure agent enrollment, reliable
patch visibility, and documented recovery procedures.

A controlled beta is not a production release.

## Release scope

Required:
- Server installation and configuration.
- HTTPS configuration and certificate trust.
- Agent installation for supported beta distributions.
- Agent enrollment, approval, and revocation.
- Agent heartbeat and patch inventory reporting.
- Functional authenticated web dashboard.
- Documented backup, upgrade, and recovery procedures.
- Offline or disposable-system acceptance testing.
- Clear user-facing installation instructions.

Excluded from initial beta:
- Unattended patch installation.
- Automatic reboots.
- Production deployment authorization.
- Guaranteed atomic multi-file upgrades.
- Advanced adversarial filesystem hardening.
- Automatic deletion of uncertain recovery journals.

## Acceptance gates

### Gate 1 — Server installation

Status: NOT YET ACCEPTED

Demonstrate a clean, repeatable installation into
an explicitly authorized disposable environment.

Verify configuration, service startup, health checks,
HTTPS, restart behavior, and uninstall/recovery guidance.

### Gate 2 — Agent installation

Status: NOT YET ACCEPTED

Demonstrate supported beta agent installation on
Arch Linux and Debian 13 disposable systems.

The current real-system installation path is disabled.
This gate cannot pass until an intentionally scoped
beta installation mechanism exists and is tested.

No installation on homelab containers is authorized.

### Gate 3 — Enrollment and security

Status: IMPLEMENTED; ACCEPTANCE PENDING

Verify enrollment, approval, credential handling,
certificate validation, revocation, and unauthorized
request rejection.

Review dashboard administrative credential handling.

### Gate 4 — Dashboard and reporting

Status: IMPLEMENTED; ACCEPTANCE PENDING

Verify authenticated access, fleet inventory,
update counts, refresh, search, lifecycle controls,
error handling, and stale-response protections.

Confirm that reporting never installs patches.

### Gate 5 — Upgrade and recovery

Status: PROTOTYPE; ACCEPTANCE PENDING

Verify upgrade and recovery in an isolated,
disposable environment.

The existing recovery journal is deliberately
retained. Finalization assessment is advisory only.

Do not represent the current upgrade prototype
as crash-safe or production-ready.

Document the manual recovery fallback and known
limitations before beta approval.

### Gate 6 — Packaging and documentation

Status: PARTIALLY IMPLEMENTED

Verify package contents, checksums, signatures,
supported platforms, version metadata, and
repeatable installation instructions.

Reconcile PROJECT-STATUS, ROADMAP,
DEVELOPER-HANDOFF, USER-GUIDE, and
RELEASE-CANDIDATE-STATUS.

### Gate 7 — Final beta acceptance

Status: NOT APPROVED

Required evidence:
- Full local regression passes.
- Required disposable-system acceptance passes.
- No unresolved critical security defects.
- Known limitations are documented.
- Release artifacts are validated.
- Explicit user approval to publish the beta.

## Execution order

1. Audit existing features against these gates.
2. Identify only genuine beta blockers.
3. Complete missing installer and user workflows.
4. Run disposable-system acceptance.
5. Reconcile documentation and release artifacts.
6. Request explicit beta publication approval.

## Safety boundaries

Do not merge, tag, publish, deploy, or enable hosted CI
without explicit approval.

Do not modify CT 102, CT 104, or existing beta VMs
without explicit approval.

Preserve local untracked data, secrets, credentials,
backups, and development artifacts.

No automatic patching or rebooting.

## Completion rule

A gate passes only with observed evidence.

Passing unit tests alone does not establish
end-to-end beta acceptance.

Do not introduce additional release blockers
without documenting the concrete risk and why
it cannot reasonably be deferred.

<!-- VERSIONARY_BATCH_75_FRESH_INSTALL_SCOPE -->
## Batch 75 — Initial controlled-beta installation scope

Decision: the first controlled beta supports fresh installations only.

In-place upgrades are deferred. No automatic patch installation,
automatic reboot, or production deployment is authorized.

The beta fresh-install planner provides read-only readiness
checks for isolated installation roots. It reuses existing
payload inventory, destination-conflict, and recovery checks.

A passing readiness plan does not install files, authorize
installation into `/`, activate systemd services, or enroll agents.

Existing payload files, including matching files, block a
fresh-install plan. Existing private agent state must be preserved.

Pending installation or upgrade recovery state blocks planning.

The real-system agent installation coordinator remains disabled.

Next acceptance milestone:
- Verify the planner and permanent regression tests.
- Review the actual fresh-install implementation boundary.
- Prepare a separately authorized disposable-VM installation trial.
- Do not claim Gate 2 accepted until that trial succeeds.
