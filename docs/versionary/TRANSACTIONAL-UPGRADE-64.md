# Versionary — Isolated Upgrade Prototype

## Batch 64

This batch introduces an isolated-root upgrade prototype with:

- Exact verification of existing installation payloads
- Private transaction directory
- Previous and proposed payload snapshots
- SHA-256 snapshot verification
- Exclusive staging-file creation
- Per-file atomic replacement
- Persistent recovery indicator
- Explicit restoration of original payloads
- Fresh-process recovery testing
- Preservation of private agent state
- Rejection of unexpected filesystem changes

## Important limitations

This is a development prototype, not a production upgrade engine.

Per-file atomic replacement does not make a multi-file upgrade
atomic.

The transaction directory is intentionally retained after
successful application or recovery. Automatic cleanup and
upgrade finalization are not implemented.

The current implementation does not provide a durable
multi-file commit protocol or guarantee recovery after power
loss, storage failure, or adversarial concurrent mutation.

No service lifecycle management, agent enrollment, certificate
rotation, or database migration is performed.

No production installation is authorized.

## Next release gates

- Review transaction journal completeness and durability.
- Add safe finalization with independent recovery verification.
- Add stronger fault injection and filesystem race tests.
- Verify real distribution payloads and upgrade compatibility.
- Run disposable VM acceptance.
- Review release provenance and publisher authenticity.
- Prepare reviewed GitHub pull request and beta release.

The real-system installer remains disabled.
