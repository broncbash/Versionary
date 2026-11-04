# Versionary — Release Candidate Status

Updated: 2026-11-04

## Development branch

feature/versionary-agent-rename

Last confirmed pushed baseline:

20c9606 — feat: harden Versionary agent installation
and document multi-VM beta

Subsequent local development is pending review and commit.

## Verified beta environment

A disposable three-VM beta demonstrated:

- HTTPS Versionary server
- Arch Linux agent
- Debian Linux agent
- Agent registration and approval
- Authenticated heartbeats
- Patch inventory reporting
- Browser dashboard visibility
- Daily reporting timers
- No automatic patch installation

The disposable beta environment is not production approval.

## Release engineering

Completed local development:

- Verified server release archive
- Unified installation kit
- Release checksum generation
- Isolated installer coordinator
- Isolated installer dependency packaging
- Persistent installation recovery indicator
- Isolated upgrade transaction prototype
- Original-payload recovery
- Private agent-state preservation tests
- Fresh-process recovery tests

The isolated upgrade prototype does not establish
power-loss-safe recovery or atomic multi-file upgrades.

## Installation safety

Real-system agent installation remains disabled.

Production deployment is not approved.

The release candidate must not be advertised as
production-ready or as a completed system installer.

## Remaining technical gates

- Review filesystem durability and transaction finalization
- Verify publisher authenticity and release provenance
- Complete disposable-VM installation and upgrade acceptance
- Review administration and credential security
- Determine which artifacts are suitable for public preview
- Review documentation for stale or conflicting guidance

## GitHub integration plan

1. Consolidate intended source, tests and documentation.
2. Verify full local regression.
3. Review staged diff for accidental sensitive content.
4. Commit and push after explicit approval.
5. Open and review a pull request targeting main.
6. Merge after explicit approval.
7. Publish a clearly labeled beta release after approval.

No hosted CI is required or authorized.

No live homelab modifications are authorized.

Preserve local beta data, certificates, credentials,
databases, backups, and other untracked artifacts.
