# Versionary — Project Status
## Repository rename and public-release checkpoint — 2026-11-06

The repository is now **public** at https://github.com/broncbash/Versionary (default branch `main`), verified using the connected GitHub integration. The `v0.1.0-beta.1` prerelease and its four release files remain present. Downloads may use unauthenticated HTTPS (`curl -fL`) from the new canonical release URLs. Public source/release access does not constitute production approval. No credentials, private keys or real enrollment material should ever be published. Dated historical sections that describe the former private name/visibility are retained as historical context.


## Current authoritative checkpoint — 2026-11-05 (v0.1.0-beta.1)

**This section supersedes historical status and publication restrictions below; older entries remain as dated engineering history.**

- GitHub repository: `broncbash/Versionary`, **public**. Default branch `main`.
- PR #2 merged into `main` at `9a3587b5edfbbd0088ecb46d802117f62f01a551`; feature branch commit `cd12d1f95a2d52d005a3623045e0efcf9084b5b3`.
- Published GitHub prerelease **v0.1.0-beta.1**: https://github.com/broncbash/Versionary/releases/tag/v0.1.0-beta.1
- Four assets uploaded: main archive, agent distribution, JSON manifest, and SHA256SUMS.
- Main archive SHA256: `4309194d3d993a0a7d1c238d0ac514963b53c80afd5263c304f36a11dc26542a`.
- Agent distribution SHA256: `936fc9c05e7b7f6d4b4c5aff4805d225da915311594af9e862797d024e76257b`.
- Main archive and manifest contain 160 release files. Local archive verification and checksums passed.
- Guided agent installation **executed successfully** on disposable Arch VM: install, registration, dashboard approval, enrollment, heartbeat, and report. No package upgrades; timer disabled by default. The later improved waiting-message text was syntax checked but not re-run on VM.
- Server: isolated HTTPS beta, `/health`, dashboard `/admin/dashboard`, explicit enrollment/reporting feature gates. Server-hosted agent distribution disabled.
- Production deployment **NOT approved**; unattended patching/reboots not implemented or authorized.
- Next work: simplify clean installs and onboarding, validate real downloaded artifacts and manifest together, improve certificate UX, agent discovery, Arch/Debian compatibility, reporting diagnostics, recovery, and security.
- Historical test totals below are dated checkpoints, **not** claims of current full-suite execution.
- Repository was made public by the user on 2026-11-06; never publish secrets or private installation state.

---

## Historical engineering documentation (preserved)

# Versionary — Project Status

## Current engineering checkpoint — 2026-11-04

The historical milestones below are retained for traceability.
This section supersedes earlier descriptions of the current
implementation, test totals, and next engineering priorities.

- Branch: `feature/versionary-agent-rename`.
- Last confirmed pushed commit before Batch 70: `f290fb3`.
- Draft GitHub PR: https://github.com/broncbash/Versionary/pull/2
- Latest local regression: 1,577 tests, one skipped, zero failures.
- Three disposable beta VMs demonstrated HTTPS server operation,
  approved Arch and Debian agents, reporting, and daily timers.
- Unified installation kit and isolated-root agent installation
  and upgrade prototypes exist.
- Isolated upgrade recovery includes strict manifest validation,
  installation/upgrade recovery exclusion, snapshot verification,
  journal parent synchronization, and fault-injection tests.
- Real-system agent installation remains disabled.
- Automatic patch installation remains disabled.
- Production deployment and release publication are not approved.

Remaining: crash consistency, transaction finalization,
concurrent filesystem mutation safety, release provenance,
administrative security, and controlled installation acceptance.

Local beta state, certificates, credentials, databases,
backups, and untracked files must be preserved.
No hosted CI or live homelab changes are authorized.

---


Updated: 2026-11-01
Repository: broncbash/Versionary
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

## Mission 5C — Active Release Integrity (2026-11-01)

Status: Implementation complete; local regression passed.

- Added read-only active release content integrity verification.
- Reused the atomic release SHA-256 module digest algorithm.
- Detects tampered, missing, unexpected, symlinked and hardlinked modules.
- Integrated fail-closed integrity checks into read-only rollback planning.
- Reports integrity separately from authenticity and provenance.
- Rollback authorization remains false; no production deployment permitted.
- Updated legacy release fixtures to use genuine content-addressed releases.
- Validation: 49 focused tests passed; 1,275 full tests passed,
  one skipped, zero failures/errors.
- Remaining hardening: race-resistant filesystem inspection,
  independently authenticated release trust, and coordinated recovery.

## Mission 5D — Descriptor-based release verification

- Replaced pathname-based module reads with descriptor-relative reads.
- Added `O_NOFOLLOW` protections for release directories, modules, and bytecode cache entries.
- Validates opened objects using `fstat`, including ownership, permissions, file type, and hardlink count.
- Rechecks file metadata and the active-release pointer during verification.
- Added seven descriptor-security regression tests.
- Validation: 39 focused tests passed; 1,282 full-suite tests run, one skipped, zero failures.
- Rollback remains read-only and unauthorized; production deployment remains blocked.
- Limitations: not an atomic filesystem snapshot; concurrent in-place writes and ABA-style replacements are not conclusively excluded; integrity is not authenticity or provenance.

## Mission 5E — Release concurrency detection

- Added pre-read module metadata capture and immediate post-read comparison.
- Rechecks module metadata after the complete release content hash.
- Rechecks release-directory path identities against opened descriptors.
- Detects persistent unexpected release-directory entries.
- Added five adversarial concurrency regression tests.
- Validation: 44 focused tests passed; 1,287 full-suite tests run, one skipped, zero failures.
- Production deployment and rollback execution remain disabled.
- Limitations: detection is not filesystem immutability or an atomic snapshot. Transient changes, metadata-preserving modification, and post-verification changes remain outside the guarantee.

## Beta 0.9 localhost acceptance checkpoint — 2026-11-01

### Verified on actual CachyOS desktop
- Persistent local HTTPS endpoint: `https://localhost:8769/admin/dashboard`.
- Actual desktop agent registered, approved, activated, authenticated, heartbeated, and reported updates to SQLite-backed server.
- `checkupdates` returned 24 available repository updates, and Versionary dashboard displayed 24. `pacman -Qu` had returned 0 because its local sync metadata was not refreshed; never interpret scanner errors as zero updates.
- Local launcher `~/.local/bin/versionary-beta09` now runs through the repository `.venv` without manual Python invocation; `status` verified local state and agent present.
- Dashboard page refresh restored administrator access in the same tab; Log out cleared access. This uses browser `sessionStorage`, **not** a server-side session or HttpOnly cookie. Do not call it production-ready authentication.
- Server was restarted after the dashboard change; user confirmed refresh and logout work.
- No package installation, update execution, reboot, live homelab CT change, or hosted CI was performed.

### Outstanding before release
- Integrate the local launcher and `checkupdates` scanner into a tested, distributable installer, without embedding checkout-specific absolute paths.
- Replace tab-scoped bearer-token storage with proper server-side sessions, HttpOnly/Secure/SameSite cookies, CSRF protection, expiry, and logout invalidation.
- Verify restart persistence, backup/restore, safe upgrades, cross-distro scanning, error reporting, and installer rollback.
- The latest local edits have not been confirmed committed/pushed at the time of this checkpoint.

---

<!-- VERSIONARY_RC2_ACCEPTANCE_20261102 -->
## 2026-11-02 — RC2 real installation milestone

Versionary RC2 passed full regression (1390 passed, 1 skipped),
release validation, real installation on cloned Arch Linux VM
192.168.122.92, verified HTTPS, and reboot persistence.

Production approval remains NO.

See RC2-REAL-INSTALL-ACCEPTANCE.md for the complete evidence and
RC2-ACCEPTANCE-OPERATIONS.md for the VM operating reference.

Next gate: destructive installation failure-recovery acceptance on a
separate disposable target.

## 2026-11-03 — Multi-distribution beta fleet acceptance

PASS — Real HTTPS beta server at 192.168.122.202:8766.

- Arch Linux agent: approved, enrolled, online, successful scan and report.
- Debian 13 agent: approved, enrolled, online, successful scan and report.
- Dashboard verified: 2 registered, 2 approved, 0 pending,
  2 online, 0 needing attention, 0 reported updates.
- Debian enrollment used the V2 registration and enrollment protocol.
- Both agents reported zero available updates.
- Agent operations were manually invoked; automatic periodic reporting
  has not yet been verified.
- Production approval remains NO.

Installer recovery hardening and two new regression test modules were
completed locally. The previously reported full regression result was
1,398 tests, 1 skipped, no failures.


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


## Batch 32 — Unified installation kit

The unified Versionary installation kit passed local acceptance
on November 4, 2026. It contains both installer entry points,
the verified 137-file server release, the agent distribution,
and the required installer resources.

The server passed release verification and dry-run acceptance.
The agent completed installation into a disposable filesystem.

Production deployment, enrollment, and service activation
were not performed.

The next deployment gate is an explicitly approved disposable
VM server installation.

See INSTALLATION-GUIDE.md.


## 2026-11-04 — Disposable VM acceptance and portability checkpoint

The controlled-beta disposable VM lab consists of:

- Arch Server: 192.168.122.249
- Arch Agent: 192.168.122.81
- Debian 13 Agent: 192.168.122.34

The Arch Server is installed and running over CA-verified HTTPS.
The server health endpoint and dashboard HTTP response were
verified. Both agent VMs reached the HTTPS health endpoint.

Arch and Debian agent disposable-root installations succeeded.
The Debian installation required python3-cryptography and revealed
a default-umask portability issue. Both issues have local fixes
and regression coverage.

Local changes:
- installer/atomic-release.py
- installer/install-versionary-agent
- tests/test_versionary_release_umask.py
- tests/test_versionary_crypto_dependency.py

Regression checkpoint:
- 2026-11-04, Batch 43D
- 1,446 tests executed
- 1 skipped
- 0 failures/errors
- git diff --check clean

The fixes are not yet committed or pushed. Existing untracked
local files and backups must be preserved.

The disposable server's enrollment, reporting, and distribution
gates remain disabled. Agent enrollment, approval, heartbeat,
reporting, and systemd activation are not yet completed in
this lab.

No live homelab containers were modified. Production deployment
remains disabled and unauthorized.


## Controlled Beta Milestone — 2026-11-04

Status: PASSED — three disposable Linux VMs.

- Arch Linux beta server: 192.168.122.249
- Arch Linux agent: 192.168.122.81
- Debian 13 agent: 192.168.122.34
- HTTPS beta server and authenticated dashboard operational.
- Both agents registered, approved, and enrolled successfully.
- Both agents completed authenticated heartbeats.
- Both agents submitted successful package reports.
- Both agents appeared online in the authenticated dashboard.
- Both reporting timers enabled for 06:00 daily.
- Automatic package installation remains disabled.
- Local regression: 1,534 tests passed, one skipped.
- Production approval: NO.
- Production deployment: NOT PERMITTED.
- Live homelab containers: UNCHANGED.


## Batch 72 — Journal integrity checkpoint

Batch 72: isolated upgrade journal inventory prechecks reject unexpected or missing entries before manifest interpretation.

## Batch 73 — Controlled beta acceptance

Batch 73 establishes BETA-ACCEPTANCE-PLAN.md as the controlled-beta acceptance checklist. The latest verified regression is 1,590 tests with one skipped. End-to-end beta acceptance remains pending.
