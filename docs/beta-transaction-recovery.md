# Isolated beta transaction and recovery design

## Status (Batch 8C.3A)

**Design and read-only intent only.** `installer/beta-transaction-plan.py` emits a deterministic description of the requested release symlink, configuration, CA certificate, service unit, and timer unit. It invokes the existing read-only destination preflight before building the plan. It neither writes a journal nor performs installation or recovery. `recovery_available` and `production_approved` are deliberately false.

## Current architecture

- `stage-beta.py` validates external inputs, calls `beta-preflight.py`, then invokes installers sequentially. The existing stage path is not a single atomic transaction.
- `atomic-release.py` atomically switches an active symlink, but does not make all five installation phases atomic together.
- `recovery-engine.py` is a disposable-only crash simulation using five byte assets; it does not represent the actual release tree or directory creation semantics.
- Existing preflight rejects conflicting destination contents and unactivated releases rather than guessing how to repair them.

## Recovery requirements before integration

1. Explicitly distinguish pre-existing files, absent files, created directories, and the release symlink. Record ownership, identity, permissions, and verified content where relevant.
2. Durable journal with a versioned schema, bounded payloads, validated state transitions, fsync ordering, and a single-writer lock. Never store private keys or enrollment secrets in a plaintext journal.
3. Fail closed if any path, symlink target, inode identity, or content changes unexpectedly. Do not delete pre-existing data or follow symlinks through untrusted ancestors.
4. Ensure rollback is idempotent after interruption; require an explicit recovery command and never start services or contact a server.
5. Cover crashes before/after each filesystem mutation, during journal publication, and during rollback. Test tampered journal and recovery sources, cross-device and permission failures, and concurrent attempts.
6. Keep the isolated beta root restriction; production deployment and automatic recovery require separate design and approval.

## Test and release gates

Run `./.venv/bin/python installer/local-readiness.py`. The baseline before this batch was 903 passing tests at local commit `eaef76d`. Do not commit or push until the new tests and full offline readiness pass. No CT 104/102 changes, no production deployment, and no main-branch merge are authorized.
