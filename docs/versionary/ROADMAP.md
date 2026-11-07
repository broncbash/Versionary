# Versionary — Development Roadmap
## Repository distribution milestone — 2026-11-06

- [x] Rename remote GitHub repository to `broncbash/Versionary`.
- [x] Make the GitHub repository public as explicitly authorized by the user.
- [x] Keep the `v0.1.0-beta.1` beta release available for direct unauthenticated HTTPS download.
- [ ] Verify downloaded artifacts and the manifest together with server dry-run on a fresh disposable VM, then test server/agent guided installation on fresh Arch and Debian environments.
- [ ] Decide on future release distribution signing, support matrix, install automation, update/rollback workflow, and production acceptance gates independently of public repository visibility.


## Current roadmap — after v0.1.0-beta.1 publication (2026-11-05)

**This section is authoritative; older milestones below remain historical.**

### Shipped in controlled beta
- GitHub prerelease with four verified downloadable assets and checksums.
- Isolated HTTPS server, authenticated administrative dashboard, agent approval/revocation, secure enrollment, heartbeat, and package-update reports.
- Guided agent installer with interactive or scripted inputs, offline distribution, optional dependency installation, administrator approval wait, initial report, and opt-in daily timer.
- Arch and Debian beta fleet acceptance in disposable VMs; guided installer live-accepted on disposable Arch VM.

### Near-term priorities
1. **First-run experience:** one-command or interactive server/agent installation, complete help, friendly error messages, clear dashboard onboarding and approval.
2. **Distribution:** verify GitHub-downloaded release/manifest pairing and release identity, stable artifact names, safe release upgrades and uninstall planning.
3. **Platform support:** clean install/reinstall/upgrade acceptance on disposable Arch/CachyOS and Debian/Ubuntu; test dependency detection and scanners.
4. **Certificates:** GUI Settings > Security > Certificates; generate/renew own CA/server cert or upload user-supplied TLS cert/key; correct hostname/IP SAN; safe CA distribution and rotation; CLI parity.
5. **Operations:** configurable scan schedules, agent health, last-seen, history, diagnostics, clear error reporting, secure backups and recovery.
6. **Discovery:** optional, secure network agent discovery with explicit authorization and no silent enrollment.
7. **Security:** review admin sessions/CSRF, enrollment, release provenance/signatures, transaction durability, concurrency, recovery and rollback; protect private state.
8. **Product polish:** responsive cyberpunk-friendly dashboard theme, filters/search, user-friendly Settings, professional branding and documentation.
9. **Later, separately authorized:** manual administrator-triggered package updates, progress/result visibility, safe controls and reboot policy. No unattended patching by default; no automatic reboot.
10. **Release readiness:** supported-platform matrix, reproducible packaging, tests, upgrade migration, security review, explicit production approval, and separate authorization for public repository visibility.

### Product constraints
- Observer-only and non-destructive by default; no automatic upgrades or reboots.
- GUI and CLI administrative feature parity where practical.
- Portable; never hard-code VM/homelab IPs, trust fingerprints, or personal paths.
- Preserve identities, credentials, CA trust, local state and recovery artifacts.
- No changes to live Proxmox containers CT 102/104 without permission.
- No commit/push/merge/tag/release/public visibility change without explicit approval.
- Historical sections below may say release publication was prohibited: those statements applied **before** the explicitly authorized beta publication.

---

## Historical engineering documentation (preserved)

# Versionary — Development Roadmap

## Current roadmap checkpoint — 2026-11-04

This checkpoint supersedes earlier next-batch statements.
Historical phase and mission records remain below.

**Implemented and verified in development:**
- Agent enrollment, approval, heartbeat, and inventory reporting.
- Disposable HTTPS multi-distribution beta.
- Unified installation kit and isolated-root installer prototype.
- Isolated upgrade preparation and explicit original-file recovery.
- Recovery-boundary, manifest, and durability regression tests.
- Full local regression: 1,577 tests, one skipped.

**Next engineering gates:**
1. Strengthen transaction durability and recovery semantics.
2. Review concurrent filesystem changes and descriptor safety.
3. Define and test explicit transaction finalization.
4. Reconcile release authenticity and provenance requirements.
5. Validate installation and upgrade on approved disposable VMs.
6. Review administrator sessions, credentials, and certificate UX.
7. Complete documentation and release acceptance.

**Not authorized:** production installation, unattended patching,
merging to main, or public release publication.

---


## Product principles

1. Observer-only by default.
2. No unattended upgrades or reboots.
3. Secure enrollment and explicit administrative approval.
4. Portable installation on supported Linux distributions.
5. GUI and CLI administrative feature parity where practical.
6. Safe, reversible upgrades with protected existing state.
7. No hard-coded homelab addresses or trust fingerprints.
8. No production deployment without explicit authorization.

## Phase 1 — Agent security and HTTPS beta

Status: Substantially implemented and tested.

- Persistent agent identity.
- Private credential storage.
- Ed25519 enrollment.
- Server approval/revocation.
- CA-verified HTTPS requests.
- Manual heartbeat and report.
- Disposable isolated HTTPS lifecycle testing.
- Security regression tests.

Remaining:
- Continue threat-model review.
- Verify all error and recovery paths.
- Address test dependency deprecation when appropriate.

## Phase 2 — Portable agent setup

Status: Foundation implemented; further development verified through commit 80a8217.

Completed:
- Interactive and unattended connection setup.
- Dry-run mode.
- HTTPS-only origin validation.
- CA path validation.
- Private configuration creation.
- Non-destructive refusal to overwrite configuration.
- Eight installer tests.

Next:
- Build self-contained distribution packaging.
- Validate actual CA PEM content and certificate chain.
- Check hostname/IP SAN during HTTPS preflight.
- Define safe state migration and upgrade behavior.
- Add uninstall planning and state retention controls.
- Provide explicit opt-in service/timer installation.
- Add offline tests for packaging, upgrades, and rollback.
- Document supported Python versions and dependencies.

## Phase 3 — Server installation and configuration

- Interactive and unattended server installer.
- Portable database and state directories.
- Configurable bind address and HTTPS endpoint.
- User-supplied certificate/private key support.
- Automatic certificate/CA generation.
- Secure certificate renewal and replacement.
- Agent CA trust distribution instructions.
- Backup and restore validation.
- Clear first-run administrator setup.

## Phase 4 — GUI administration

- Settings > Security > Certificates.
- Certificate upload and automatic generation.
- Agent registration and approval workflow.
- Agent health, update inventories, and history.
- Filters, search, and actionable diagnostics.
- Role and permission review.
- GUI/CLI configuration parity.
- Responsive, accessible interface.

## Phase 5 — Release readiness

- Clean install on disposable Arch and Debian systems.
- Upgrade, rollback, reinstall, and restore testing.
- Certificate rotation and revoked-agent testing.
- Negative tests for unauthorized operations.
- Installer and artifact integrity verification.
- Documentation and command-reference validation.
- Security review and production acceptance checklist.
- Explicit production deployment approval.

## Definition of done for an installer

An installer is not production-ready until it:

- Requires explicit consent before making changes.
- Has an accurate dry-run/plan mode.
- Preserves existing credentials and identities.
- Never silently replaces trust anchors.
- Does not automatically enroll or activate reporting.
- Handles failed installs and interrupted upgrades safely.
- Documents every file and service it creates.
- Has verified clean-install and upgrade tests.

## Deferred decisions

- Final supported operating systems and versions.
- Packaging format and distribution mechanism.
- Default service/timer scheduling policy.
- Agent discovery mechanism and its security model.
- Long-term database backend and migration policy.
- Final product branding and repository rename.


## November 2026 engineering checkpoint

Verified repository checkpoint: 80a8217.

- Dashboard lifecycle controls use the isolated HTTPS beta administrator
  route namespace.
- Explicit revocation confirmation and stale-response protection are
  covered by browser behavior tests.
- Dashboard regression: 27 tests passed.
- Route compatibility: 2 tests passed.
- Full local unittest discovery completed successfully (exit status 0).
- Disposable HTTPS beta enrollment/reporting demonstrated previously.
- No authorization for production deployment or automatic patching.

### Next implementation batch: coordinated transaction planning

Implement a read-only planner based on
docs/COORDINATED-ROLLBACK-DESIGN.md.

The planner must:

- Never modify installed assets.
- Reject unsafe roots and symlinked inputs.
- Inventory versioned releases, configuration, CA trust and unit files.
- Identify missing assets, unsafe permissions and incompatible layouts.
- Report planned changes and recovery blockers in structured output.
- Require explicit operator-selected paths.
- Never enable systemd services or contact production servers.

Follow with disposable fault-injection tests before designing an
authorized apply/rollback workflow.

Production approval remains NOT GRANTED.

## Mission 5B — Release-aware rollback planning

Status: **Implementation complete; full regression passed (2026-11-01).**

Delivered:
- Read-only active-release inspection.
- Integration with the existing rollback planner.
- Partial-installation and unsafe-path regression coverage.
- Backward-compatible four-asset snapshot schema.

Remaining before coordinated rollback can be considered:
- Authenticate trusted release contents and rollback targets.
- Design race-resistant filesystem inspection and transaction locking.
- Coordinate code, configuration, CA trust, and systemd lifecycle recovery.
- Expand disposable fault-injection and interruption testing.
- Obtain explicit approval before any deployment or rollback execution.

## Mission 5C — Release Integrity Milestone

Completed locally on 2026-11-01:

- Read-only active release content integrity verification.
- Fail-closed rollback planning when active release integrity fails.
- Explicit separation of integrity, authenticity, provenance and authorization.
- Full local regression: 1,275 tests, zero failures, one skipped.

Next security priorities:

1. Race-resistant release inspection and file-descriptor-based verification.
2. Independently authenticated trust for installed release identities.
3. Coordinated rollback transaction design and fault-injection testing.
4. Production deployment remains blocked pending explicit approval.

## Mission 5D — Descriptor-based verification

Status: local implementation and regression validation complete; awaiting commit.

Completed:
- Descriptor-relative module and bytecode inspection.
- Symlink and hardlink defenses.
- Active-pointer identity recheck.
- Additional security regression coverage.

Remaining before production eligibility:
- Stronger immutable-release or snapshot guarantees.
- Trusted release authentication and provenance integration into the decision path.
- Coordinated, authorized recovery and service lifecycle.
- Explicit production acceptance and approval.

## Mission 5E — Concurrency hardening

Status: local implementation and regression validation complete; awaiting commit.

Completed:
- Pre-read and post-read module metadata comparisons.
- End-of-verification module metadata checks.
- Release-directory identity rechecks.
- Persistent directory-entry change detection.
- Five additional adversarial regression tests.

Future security work:
- Define an immutable-release lifecycle and threat model.
- Evaluate snapshot or other filesystem-backed consistency mechanisms.
- Bind verified release identity to the subsequent authorized operation.
- Integrate trusted authenticity and provenance into that decision.
- Preserve explicit production approval and fail-closed recovery behavior.

## Beta 0.9 localhost acceptance checkpoint — 2026-11-01

### Beta 0.9 acceptance milestone (2026-11-01)
- [x] Persistent localhost HTTPS server and actual approved CachyOS agent.
- [x] Actual update inventory reported and displayed: 24 via `checkupdates`.
- [x] Local launcher uses project virtual environment without manual interpreter prefix.
- [x] Dashboard remembers bearer token across refresh in the same tab and offers Log out.
- [ ] Portable release installer; current launcher wrapper contains a developer checkout path.
- [ ] Proper server-side admin sessions with secure cookies, CSRF protection, expiry and invalidation.
- [ ] Restart persistence, upgrades, backups, installer rollback and multi-distro release acceptance.
- [ ] Formal production security review and deployment approval.

---

<!-- VERSIONARY_RC2_ACCEPTANCE_20261102 -->
## RC2 acceptance roadmap update

Completed: full regression, hardened release verification, real installer
execution, systemd startup, trusted HTTPS, IP certificate validation,
and automatic service startup after reboot.

Next: preserve known-good VM; test destructive installer failure recovery
on another disposable target; harden cleanup exception handling; rerun
regression; rebuild release if necessary; complete beta acceptance review.

Future: portable installers, GUI/CLI configuration parity, certificate
management, agent trust workflows, and controlled GitHub integration.

## 2026-11-03 — Beta fleet milestone

Completed:
- Secure enrollment and authenticated reporting on Arch Linux and Debian 13.
- Two-agent fleet visibility in the HTTPS dashboard.

Next priorities:
- Portable, dependency-complete agent packaging and installation.
- Automatic heartbeat and periodic package-update reporting.
- Improved agent setup diagnostics and consistent state-directory handling.
- Disposable VM failure-recovery acceptance for the hardened server installer.
- Release candidate rebuilding and validation before broader deployment.

Production deployment remains unapproved.


## Agent Installer Checkpoint — Batch 26U

The consolidated offline agent installer has passed
permanent end-to-end regression testing.

Verified:
- 1,432 regression tests executed successfully (1 skipped).
- Seven permanent installer integration tests passed.
- Complete installation into an isolated filesystem.
- Idempotent reinstallation.
- Preservation of existing identity and credentials.
- Rejection of conflicting CLI and CA destinations.
- Recovery from a simulated interrupted installation.
- No automatic registration or service activation.

Current implementation:
- Verified agent distribution archive.
- Administrative CLI with system-mode support.
- Offline installation coordinator.
- Agent modules, CA, configuration, and systemd units.

Outstanding:
- Complete destination preflight.
- Publisher authenticity verification.
- Comprehensive rollback/recovery policy.
- Stable distribution artifact naming.
- Clean Arch and Debian installer validation.
- Controlled beta deployment acceptance.

Production deployment remains unauthorized.

See AGENT-INSTALLER-READINESS.md for details.


## Unified installation milestone

Completed:
- Portable agent installation acceptance
- Verified server release packaging
- Server installer dry-run acceptance
- Unified server-and-agent installation kit

Remaining:
- Automated unified-kit integration acceptance
- Approved disposable-VM server installation
- Server-to-agent enrollment and connectivity
- Production installer and certificate workflow
- Controlled-beta authorization

Production deployment remains disabled.


## 2026-11-04 — Disposable VM acceptance and portability checkpoint

Completed in the current disposable VM acceptance phase:

- Installed Versionary server on a disposable Arch VM.
- Verified CA-trusted HTTPS from Arch and Debian agent VMs.
- Completed both agent preflight checks.
- Completed both disposable-root agent installations.
- Added missing-cryptography guidance for Debian/Arch.
- Fixed atomic release creation under umask 0002.
- Passed 1,446 local regression tests with one skipped.

Next milestone: end-to-end live agent acceptance in disposable VMs.

Required acceptance criteria:
- Explicitly gated server enrollment and reporting.
- Secure agent installation with protected private state.
- Administrator-controlled enrollment and approval.
- Authenticated heartbeat and update inventory submission.
- Verified visibility in the server dashboard.
- Safe restart, reinstall, and rollback behavior.
- No unattended package upgrades or reboots.
- No impact on live homelab systems.

The existing disposable-root agent installer does not activate
services or enroll agents. A separate, reviewed, explicitly
authorized real-system VM workflow is required.

Before any distribution or GitHub integration, rebuild the kit
with current local fixes and rerun acceptance checks.

Production deployment remains prohibited without explicit approval.


## Completed Milestone — Multi-Distribution Controlled Beta

Completed 2026-11-04:
- Real HTTPS beta server installation.
- Real Arch and Debian 13 agent installations.
- Administrator approval and agent enrollment.
- Authenticated heartbeats and package reporting.
- Scheduled daily reporting.
- Authenticated two-agent dashboard verification.

Next:
1. Review and integrate staged installer hardening.
2. Verify upgrade, rollback, and recovery behavior.
3. Review TLS, credentials, and administrator security controls.
4. Complete release documentation and packaging.
5. Obtain explicit approval before production deployment.

Production deployment remains blocked.


## Batch 72 — Journal integrity checkpoint

Batch 72 checkpoint: journal inventory hardening is implemented; race-resistant recovery and durable finalization remain open.

## Batch 73 — Controlled beta acceptance

Batch 73 prioritizes beta acceptance gates: installation, enrollment/security, dashboard, upgrade/recovery, packaging, and final approval. Further speculative hardening is deferred unless a concrete release blocker is identified.

---

## Beta.2 checkpoint — 2026-11-06

Completed in local candidate: 1,700 Python tests (one skipped), both root-wrapper shell syntax checks, release checksums and 160-file archive/manifest verification. Guided bootstrap improvements include LAN discovery, public CA fingerprint verification, and privilege handling.

Next: audit release contents for unintended untracked installer files; synchronize root-wrapper beta.2 pins; publish exact verified four-asset prerelease; test clean server and Arch/Debian agent VMs; capture failures and update documentation. No production authorization, automatic patching, unattended reboot, or live homelab changes.
