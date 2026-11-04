# Versionary — Release Candidate Status

Updated: 2026-11-04

## Development branch

feature/versionary-agent-rename

Last confirmed pushed milestone before this batch:

f290fb3 — fix: persist isolated upgrade journal
before replacement

Recent hardening milestones:

- 90f36d4 — coordinate installation and upgrade recovery
- 777b9ad — validate upgrade snapshot identities
- 9f65e89 — reject malformed upgrade manifests
- f290fb3 — synchronize journal parent before replacement

GitHub draft pull request:
https://github.com/broncbash/arby-patch-command/pull/2

The draft targets main and is not approved for merge.
The cumulative branch contained 299 commits beyond main,
zero behind, at the comparison following 9f65e89.
This is historical comparison data, not a live mergeability
or approval determination.

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
- Shared installation/upgrade recovery boundary
- Strict snapshot identity and manifest JSON validation
- Journal parent-directory synchronization before replacement
- Simulated synchronization-failure recovery tests

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


## Batch 71 — Read-only finalization assessment

Development checkpoint: 2026-11-04.

Added a conservative advisory assessment of isolated upgrade
recovery state.

The assessment verifies original payload restoration and
identifies unexpected journal entries.

A review candidate is NOT cleanup authorization.

The transaction journal remains present and blocks
subsequent installation or upgrade attempts.

No journal deletion, transaction finalization, real-system
installation, or production deployment is enabled.

Further work is required for durable cleanup, concurrent
filesystem mutation safety, and crash recovery.
