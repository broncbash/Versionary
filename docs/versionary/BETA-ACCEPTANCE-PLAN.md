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

<!-- VERSIONARY_BATCH_76_FRESH_EXECUTION -->
## Batch 76 — Controlled fresh-install execution

The initial controlled-beta installation scope remains
fresh installations only. In-place upgrades are deferred.

The new fresh-install coordinator connects the Batch 75
readiness planner to the existing isolated-root transaction
writer.

Default mode performs a read-only installation preview.

Execution requires both:
- `--execute-isolated`
- `--authorize-isolated I_AUTHORIZE_ISOLATED_VERSIONARY_BETA_INSTALL`

The isolated root must be an absolute, safe directory other
than `/`. The existing installer rejects live-system roots.

Before execution, the coordinator repeats the fresh-install
readiness checks. Existing payloads and pending installation
or upgrade recovery state block installation.

Successful isolated execution installs the five existing
coordinator payloads. It does not enable services, enroll
agents, install patches, or authorize production deployment.

The existing transaction writer handles ordinary exceptions
with rollback and preserves a journal when recovery requires
review. It does not guarantee crash-safe or power-loss-safe
atomic installation.

This is an internal controlled-beta implementation milestone,
not an accepted production or disposable-VM deployment.

Remaining Gate 2 work:
- Validate the actual release artifact and full agent payload.
- Complete the separately gated real-system fresh-install path.
- Perform an explicitly authorized disposable-VM acceptance test.
- Verify Arch and Debian 13 agent behavior after installation.
- Document manual recovery and clean-install limitations.

<!-- VERSIONARY_BATCH_77_FULL_FRESH -->
## Batch 77 — Complete isolated fresh agent installation

A new full fresh-install coordinator integrates the existing
verified offline installer with the fresh-only readiness checks.

The complete isolated installation includes the 13-module
agent release, administrative CLI, CA certificate, configuration,
systemd service and timer definitions, and private state directory.

Preview mode does not install. Execution requires the isolated
authorization phrase and an explicit execution flag.

Existing agent installations, nonempty application/state
directories, and pending installation/upgrade journals are
rejected. No in-place upgrades are supported.

This is not a globally atomic installation: the underlying
offline installer uses multiple stages, and interruption can
leave partial state requiring manual review.

Real-system installation, service activation, enrollment,
automatic patching, and production deployment remain disabled.

Disposable-VM acceptance on Arch and Debian 13 still requires
separate explicit authorization.
