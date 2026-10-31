# Versionary Trust-State Operations

**Status:** Development only. Not approved for production deployment.

## Current implementation

Versionary provides transactional SQLite trust-state storage and a
development-only administrative CLI.

Files:
- installer/release-trust-state.py
- installer/release-trust-admin.py
- installer/release-policy-updates.py

The trust database stores the pinned Ed25519 authority public key,
authority fingerprint, accepted policy version, policy SHA-256 digest,
and exact policy bytes.

Authenticated policy updates must have valid authority signatures
and strictly increasing versions.

## Existing CLI operations

Bootstrap:
    python installer/release-trust-admin.py bootstrap
        --database /private/directory/trust.db
        --authority-public /path/authority.pem

Inspect:
    python installer/release-trust-admin.py inspect
        --database /private/directory/trust.db

Install:
    python installer/release-trust-admin.py install
        --database /private/directory/trust.db
        --policy /path/policy.json
        --signature /path/signature.json

These are illustrative commands. Options must be supplied together
on a single command line or with appropriate shell continuations.

## Backup requirements — not yet implemented

- Capture a transactionally consistent state.
- Preserve exact authority public key and policy bytes.
- Preserve policy version and SHA-256 digest.
- Do not export private signing keys or credentials.
- Require restrictive destination permissions.
- Reject unsafe directories and symlinked destinations.
- Fail closed on incomplete or interrupted exports.

A backup alone does not prove freshness.

## Recovery requirements — not yet implemented

- Never overwrite an existing database implicitly.
- Authenticate recovered policy data.
- Require the existing authority identity to match.
- Reject lower policy versions.
- Reject conflicting policies at the same version.
- Preserve existing state when validation fails.
- Apply accepted transitions atomically.
- Do not silently reset state to version zero.

For a missing database, require independently trusted authority
information and an explicit recovery procedure.

## Security limitations

A privileged attacker may replace the SQLite database or restore
an older, internally valid database snapshot.

A digest stored alongside the data it protects cannot independently
authenticate the entire database.

A local policy version does not provide independent rollback protection.

Directory restrictions and pathname checks reduce exposure but do not
eliminate every filesystem race.

Full rollback resistance requires independently protected monotonic
state or an equivalent trusted freshness mechanism.

## Required recovery tests

- Valid backup and recovery
- Corrupt or truncated artifacts
- Authority mismatch
- Invalid signatures
- Older-version rollback attempts
- Same-version conflicting policy
- Interrupted writes
- Concurrent operations
- Unsafe paths and symlinks
- Missing or damaged database
- State preservation after rejection
- CLI exit codes and diagnostics

## Deployment restrictions

Do not change CT104, CT102, production agents, or running services
without explicit approval.

Do not enable the production installer.

Do not merge, tag, or publish a release based solely on development
test results.

Update this documentation alongside substantial code changes.


## Development snapshot export — Phase VI-B

The development CLI now supports a transactionally consistent
trust-state snapshot export.

Example (one shell command):

    python installer/release-trust-admin.py export --database /private/trust.db --destination /private/backup.json

The destination must be an absolute path inside an existing
owner-controlled private directory. Existing files are not overwritten.

The export contains authority public-key material and policy bytes.
It does not contain signing private keys or agent credentials.

The snapshot includes a SHA-256 integrity digest and strict structural
validation. This digest is NOT a digital signature.

**An export is not proof of authenticity or freshness.**

Do not restore an export by directly copying it over an existing
trust database. Authenticated recovery remains unimplemented.

Outstanding engineering work includes recovery authorization,
independent freshness anchoring, and more extensive concurrency,
crash-durability, and filesystem-race testing.

## Phase VI-C1 — Existing-database authenticated recovery

Development-only command:

    python installer/release-trust-admin.py recover --database /private/trust.db --authority-public /trusted/authority.pem --policy /signed/policy.json --signature /signed/policy.sig.json --minimum-version 12

The authority must be independently trusted. The minimum version
must come from an independently trusted source, not the database
being recovered or an unauthenticated snapshot.

The command authenticates exact policy bytes using Ed25519,
rejects authority mismatches, older versions and same-version
conflicts, and applies newer versions in one SQLite transaction.

An identical same-version policy is an authenticated no-op.

This command does not create missing databases, restore snapshots,
change running services, or enable the production installer.

The CLI cannot establish that the supplied minimum version is
genuinely current. An untrusted or outdated floor remains a
rollback risk. Signed historical policies can still be replayed
after privileged replacement of the entire trust database unless
independent monotonic state is enforced.

Remaining: missing-database recovery, durable signature retention,
independent freshness anchoring, additional filesystem-race and
crash testing, and GUI/CLI parity.

## Phase VI-C2A — Missing-database recovery (development only)

Command:

    python installer/release-trust-admin.py recover-new --database /private/new-trust.db --authority-public /trusted/authority.pem --policy /signed/policy.json --signature /signed/policy.sig.json --minimum-version 12

Requires a missing database, private directory, independently
trusted authority and independently trusted positive version floor.
Authenticates the signed policy before creating the database.

Current limitations: the bootstrap and install steps reread inputs
and are not one atomic operation. A failure after creation can leave
a partial database requiring manual investigation. Do not automatically
delete or retry over an existing artifact. A privileged attacker can
still replace or roll back database files. Do not use in production.

Next: single-read immutable inputs, atomic staging/promotion,
durable signature evidence and stronger filesystem safety.

## Phase VI-C2B — Staged database publication

The development recover-new path now captures authority, policy and
signature inputs once, authenticates them before creating files,
builds and validates a private SQLite staging database, then
publishes using an exclusive hard link.

An existing database is never replaced. Normal exceptions clean
up staging files; a process crash may leave an orphaned staging
file for operator investigation.

The destination is complete before publication, but directory
fsync failure after publication may still produce an error even
though the destination exists. Inspect the database before retrying.

The private directory must not be writable by an adversary.
This is not a complete defense against privileged filesystem
replacement or rollback. Signed evidence is not yet retained
inside the database. Production deployment remains blocked.

## Phase VI-C2C — Fault-injection verification

Development tests now exercise staging database failures,
concurrent destination creation, pre-publication fsync failure,
and post-publication fsync failure.

A post-publication synchronization error may leave a complete
destination even when the command reports failure. Operators must
inspect the destination before retrying.

These simulated failures do not replace real process-kill,
power-loss, or filesystem durability testing.
