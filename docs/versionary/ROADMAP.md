# Versionary — Development Roadmap

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

Status: Foundation implemented at commit 681e8b4.

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
