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
