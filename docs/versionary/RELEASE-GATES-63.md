# Versionary — Release Gates (Batch 63)

## Verified scope

- Packaged isolated-installer dependency inventory.
- Isolated installation from extracted package contents.
- Idempotent reinstall.
- Preservation of private agent state during identical reinstall.
- Rejection of conflicting upgrades without overwriting existing files.
- Persistent recovery marker detectable after a new Python process starts.
- Explicit manual recovery review when payload files remain.
- Real-system installation remains disabled.

## Important limitations

A new process detecting an interrupted-operation journal is
not proof of crash consistency, atomic installation, or
power-loss-safe recovery.

The isolated installer currently rejects differing existing
payloads. It does not implement an upgrade transaction.

The installation journal does not yet provide durable,
fully coordinated crash recovery.

The release package checksum is not independent proof of
publisher authenticity.

No production installation is authorized.

## Remaining release requirements

- Real package and release authenticity policy.
- Coordinated upgrade and rollback lifecycle.
- Crash/power-loss durability assessment and fault injection.
- Clean disposable-VM installation and upgrade acceptance.
- Security review of browser administration and session handling.
- Final release metadata and artifact provenance review.
- Approved pull request, merge and GitHub beta publication.

No changes to live homelab containers are authorized.
