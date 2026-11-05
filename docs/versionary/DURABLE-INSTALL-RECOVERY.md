# Versionary Durable Installation and Recovery

## Status

Development-only isolated-root prototype.

This implementation introduces a persistent installation
intent journal and explicit verification before completion.

It does not enable real-system installation.

## Installation sequence

1. Validate the isolated root and payload manifest.
2. Refuse an existing recovery journal.
3. Validate existing destination files and parent chains.
4. Exclusively create the intent journal.
5. Flush journal contents and synchronize its directory.
6. Run the existing isolated transaction engine.
7. Verify all expected files against the journal.
8. Remove the journal only after successful verification.
9. Synchronize the journal directory.

## Interrupted installation

If a process stops after intent creation, the journal
remains as a recovery marker.

Subsequent installation attempts are blocked.

The inspection command reports whether expected files
are absent or match the journal.

A mismatched or unsafe file causes inspection to fail.

No automatic rollback or deletion is performed.

## Read-only inspection

```bash id="zrwv84"
.venv/bin/python \
  installer/versionary-agent-durable-install.py \
  --root /path/to/isolated-root \
  --inspect
```

## Recovery policy

- Incomplete installation: stop and review.
- Matching complete installation: eligible for explicit
  manifest-verified finalization.
- Mismatched payload: refuse finalization.
- Unknown or corrupt journal: refuse recovery.
- Existing unrelated files: preserve.
- Existing identity and credentials: never delete.
- No automatic service or timer activation.
- No automatic enrollment.

## Important limitations

This is not a fully crash-atomic installer.

Filesystem synchronization improves durability but
cannot guarantee behavior across all filesystems,
storage controllers, or power-loss conditions.

The underlying transaction engine still performs
multiple file publications and rolls back ordinary
exceptions. Crash interruption can leave partial files.

The prototype has no automatic crash rollback.
A durable journal is a recovery marker, not proof
that an installation is safe to activate.

There is no authorization to write to the real
system root.

## Next milestone

Integrate durable recovery into the complete
13-module installation workflow, then validate
fresh-install and interrupted-install scenarios
in disposable offline environments.

Only after that should the real-system deployment
path be considered for an explicitly approved,
snapshotted disposable VM.
