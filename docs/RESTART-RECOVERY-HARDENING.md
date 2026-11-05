# Disposable restart recovery: interruption and tamper matrix

This harness is an **isolated experiment**, not a production installer or rollback tool. Its public CLI creates a new private temporary directory and does not accept an installation root. The internal `_worker` command is exclusively for subprocess tests and must never be exposed as a supported installer interface.

## Coverage

- Five switch interruption checkpoints crossed with five recovery interruption checkpoints (25 combinations).
- A third independent process checks idempotent recovery.
- Journal, backup and active-generation corruption refusal.
- Symlinked journal, backup, active file and restore staging refusal.
- Per-file writes are synced; atomic rename operations are followed by parent-directory fsync. This is **not** an atomic multi-asset transaction.
- Prior-generation checksums and active-generation allowlists are verified before restoration starts.
- An interrupted recovery writes a `recovering` journal state and can be retried.

Run with `python installer/restart-recovery-trial.py --stop-at ca --recover-stop-at service`. To exercise a refusal, use `--tamper backup`. The main desktop checkpoint is `bash installer/local-check.sh --protocol-check`.

## Explicit limitations

The trial uses deterministic placeholder bytes, not real agent configuration, TLS keys or service units. The manifest has checksums but **no cryptographic authenticity**. The internal worker assumes a parent-owned disposable directory; it is not hardened for arbitrary attacker-controlled filesystem trees or concurrent writers. Crash durability is only partially modeled; fsync does not substitute for power-loss tests or filesystem-specific guarantees. Cleanup after interrupted recovery is not yet a production design. No service is started, no real host paths are modified, and no enrollment is performed.

**Deployment gate remains closed.** A production transaction needs ownership verification, directory-fd-based filesystem confinement, locking, durable backup custody, authenticated provenance, power-loss validation, explicit user approval and an independently reviewed rollback policy.
