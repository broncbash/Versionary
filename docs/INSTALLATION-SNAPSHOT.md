# Isolated installation asset snapshots

The experimental `installer/installation-snapshot.py` copies selected configuration, public CA, and inactive systemd unit files from a **disposable non-root installation** into a new private snapshot directory. It records file modes, sizes and SHA-256 digests, then verifies copied bytes. Snapshot destination must be absent and its parent private (0700); snapshot entries use mode 0600.

```bash
python installer/installation-snapshot.py --root /path/to/disposable-root --destination /path/to/private-parent/snapshot
python installer/installation-snapshot.py --destination /path/to/private-parent/snapshot --verify-only
```

The inventory explicitly excludes private state and enrollment credentials. Existing snapshot destinations are never overwritten. An incomplete snapshot is left for investigation, not silently treated as complete.

**Not a full backup or rollback solution:** no restoration is provided, no credential or private state recovery is supported, and no service state is captured. The snapshot is not authenticated against an external trust anchor; an attacker able to replace both payload and manifest may forge a consistent snapshot. Concurrent source modification is checked but cannot provide an atomic multi-file snapshot. The real filesystem root is forbidden and production installation remains disabled. Review and test restoration, crash consistency, and trusted backup storage before any live rollout.
