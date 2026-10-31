# Versionary — Homelab-First Development Roadmap

Status: Development planning. No production deployment authorized.

## Decision

Prioritize delivering a useful, read-only Versionary dashboard to the
owner's homelab before completing all public Release Candidate work.

The long-term product must also provide authenticated controls for
updating an individual machine and updating an explicitly selected fleet.

## Latest verified checkpoint

- Feature branch commit: 82f0350
- Full regression: 1,161 tests, one skipped, zero failures
- Isolated agent beta evaluation: PASSED (user-reported)
- Package build and integrity audit: PASSED
- Disposable TLS protocol check: PASSED
- Production installed: NO
- Agent enrolled: NO
- Host modified: NO
- External network requests: NO

These results do not demonstrate a complete deployed fleet dashboard.

## Phase VII — Homelab Observer Beta (immediate priority)

1. Audit existing dashboard, inventory and scan-reporting workflows.
2. Review docs/DEPLOYMENT-BETA-GATE.md and identify unresolved blockers.
3. Test server and agents in disposable Arch and Debian environments.
4. Verify update counts, package details, timestamps, stale-agent
   indicators, failures and refresh behavior.
5. Prepare backup, rollback and removal instructions.
6. Request explicit approval for each production deployment target.
7. Roll out a read-only beta only after safety gates pass.
8. Validate actual homelab reporting without enabling remote updates.

Acceptance: one dashboard provides reliable update visibility across
approved homelab machines without SSHing into each machine.

## Phase VIII — Remote Update Controls

See docs/REMOTE-UPDATE-CONTROLS.md.

1. Design authenticated, narrowly scoped update jobs.
2. Implement simulated execution and adversarial tests.
3. Add per-machine Update control with explicit confirmation.
4. Add fleet-wide Update All with target selection and confirmation.
5. Provide progress, results, audit logs and partial-failure handling.
6. Test actual APT and pacman operations on disposable machines.
7. Require separate explicit approval before production activation.

No automatic patching or rebooting by default.

## Public RC1

Resume remaining release hardening, clean installation, packaging,
security review, durable recovery and release-manifest validation.

RC1 scope and ordering must be revisited after the observer beta.
Do not merge or tag until the release gates are satisfied.

## Standing constraints

- Never change CT104, CT102, or production agents without approval.
- Keep the production installer disabled.
- Preserve existing running services and update visibility.
- Preserve local untracked beta assets, timer previews, backups
  and return-prompt.md.
- Update this roadmap and operational documentation with each
  substantial milestone.

## Phase VII-A — Verified desktop acceptance

Checkpoint: 2026-10-31

- Isolated agent beta evaluation: PASSED.
- Disposable package build, staging, repeat staging and integrity: PASSED.
- Loopback HTTPS protocol acceptance: PASSED.
- Real Arch desktop scan: SUCCESS, 109 available updates.
- Authenticated agent report and inventory integration: PASSED.
- Agent health in inventory: ONLINE.
- Dashboard HTTP route: PASSED.
- Clean-checkout beta09 readiness audit: PASSED.
- Recovery/security regression: PASSED.
- No production installation or enrollment.
- No homelab containers modified.
- Protected local development assets remain untouched.

### Phase VII-B — Next development stage

1. Prepare a fresh disposable Arch test environment.
2. Validate the agent's prerequisites and installation lifecycle.
3. Repeat installation and verify integrity.
4. Test failure recovery and clean removal.
5. Repeat equivalent acceptance on Debian.
6. Connect disposable server and agent over trusted HTTPS.
7. Verify real reports in a running browser dashboard.
8. Produce a reviewed, reversible homelab beta deployment plan.
9. Obtain explicit target-by-target approval before any live changes.

The existing production installer remains disabled. No CT104, CT102,
or production agent changes are authorized by this checkpoint.

### Phase VII-B — Disposable cross-distribution staging acceptance

**Result: PASSED — Arch Linux and Debian 12.**

- Built disposable test images with Python 3.14.9 (Arch) and Python 3.11.2 (Debian 12).
- Built and validated the Versionary agent distribution archive.
- Generated a temporary CA with CA basic constraints and certificate-signing key usage.
- Both distributions passed initial staging, repeat staging, and read-only integrity verification.
- Both container acceptance runs exited with code 0.
- No production installation, systemd startup, agent enrollment, or network requests occurred.
- Discovered Debian 12's older `cryptography` API lacks `not_valid_before_utc` and `not_valid_after_utc`.
- Updated CA validity checks to support both older naive-UTC and newer timezone-aware properties without relaxing certificate validity requirements.
- Added three regression tests covering valid, expired, and not-yet-valid certificates through the legacy API.
- All eleven targeted CA tests passed.

**Remaining Phase VII-B gates:** live service execution, authenticated HTTPS agent-to-server integration in a disposable environment, browser dashboard verification, recovery/removal acceptance, and a reviewed homelab deployment plan requiring explicit approval.

## Future dashboard enhancement — Distribution icons

Replace temporary distribution-letter badges with recognizable
distribution logos/icons.

- Support CachyOS, Arch Linux, Debian, Ubuntu, Fedora and other
  supported distributions.
- Use local bundled assets rather than external icon services.
- Preserve accessible text labels and a generic Linux fallback.
- Keep icons consistent with Versionary's dark dashboard theme.
- Verify safe asset handling, responsive layouts and browser rendering.

Deferred until after the homelab observer beta is operational.
