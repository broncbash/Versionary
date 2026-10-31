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
