# Coordinated rollback — design gate (not implemented)

**Status:** engineering design only. No production installer, automated rollback, service changes or deployment authorization.

## Scope and invariants

A future transaction must coordinate (1) immutable versioned code release, (2) configuration, (3) trusted CA bundle, and (4) installed systemd unit/timer definitions. Private state, enrollment credentials, SQLite databases and user-owned material are explicitly excluded from destructive rollback. Rollback must never silently revert a database schema or invalidate agent credentials.

- Default behavior is **plan-only**. Any real installation must require a separate explicit, reviewed authorization gate.
- Acquire a single-host installation lock before preflight, staging, commit or recovery. Never infer a safe target from the machine running the command.
- Validate a configured installation root, ownership, modes, available space, source integrity, unit paths and trusted backup destination. Reject symlinks, hardlinks, traversal, unexpected files and unsupported layouts.
- Record an authenticated or otherwise independently trusted recovery manifest; a self-consistent SHA-256 snapshot is insufficient against malicious replacement.
- Preserve previous release and asset generations until operator-confirmed completion. Do not overwrite the only rollback copy.
- A durable journal must contain transaction ID, old/new release identifiers, per-asset digests and modes, and explicit state transitions. Flush files and parent directories at each durable boundary.
- All filesystem writes should stage in the same filesystem as their final destination. A single rename cannot atomically switch code, CA, config and systemd files together.
- No automatic service start, reload, reboot, agent enrollment, package upgrade or network access during rollback preparation.

## Proposed state machine

| State | Durable evidence | Recovery behavior |
|---|---|---|
| planned | validated inputs and intended changes | no writes to installed assets |
| prepared | trusted backups, staged assets, manifest | discard uncommitted staging after inspection |
| applying | journaled step and old/new digests | stop, inspect, then resume or reverse in controlled order |
| assets-switched | all installed assets match new generation | verify before any service lifecycle action |
| verified | integrity checks passed | operator may separately authorize service actions |
| committed | operator-approved completion marker | retain backup per retention policy |
| recovery-required | failed or interrupted step | refuse another install until explicit recovery |

## Failure matrix to test

1. Crash before backup, during snapshot, after backup, and between each file switch.
2. Disk full, permission denied, injected I/O failure, power loss, and mismatched hash at each boundary.
3. Missing old release, tampered journal, stale lock, symlink substitution and backup path outside trusted storage.
4. Config/CA mismatch, invalid certificate SAN, expired CA, incompatible service unit and unsupported schema migration.
5. Concurrent installer attempts and manual operator edits between plan and apply.
6. Repeated recovery, repeated install and rollback after an already completed recovery.
7. No service action without authorization; no private state deletion or credential exposure.

## Immediate implementation boundary

The existing isolated asset snapshot/restore tools are **not** this transaction. Restoration currently targets an empty disposable root only; a partial restore is left intact for investigation. The next safe code milestone is a **read-only transaction planner** that reports old/new assets and blockers, followed by disposable fault-injection trials. Do not enable production install or merge to `develop`/`main` without explicit approval.
