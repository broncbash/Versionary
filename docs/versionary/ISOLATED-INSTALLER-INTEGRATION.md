# Versionary — Isolated Installer Integration

## Batch 62

This integration connects the existing agent installation
components through a single isolated-root coordinator.

Components:

- Distribution, HTTPS server and CA preflight
- Expected payload construction
- Filesystem conflict inspection
- Existing content comparison
- Installation transaction
- Persistent journal inspection
- Conservative recovery review

## Safety boundaries

The coordinator rejects the real system root `/`.

It does not:

- Install to the running operating system
- Start or enable systemd services
- Register or enroll agents
- Modify packages or reboot machines
- Overwrite differing installation files
- Automatically delete files after interrupted operations

An unresolved installation journal blocks subsequent installation
until recovery is explicitly reviewed.

## Limitations

The transaction engine provides exception rollback, not
guaranteed crash consistency.

The journal is a conservative recovery indicator, not a complete
write-ahead transaction log.

Existing-file validation and filesystem publication are not
fully race-free against concurrent privileged modifications.

Publisher authenticity and production deployment authorization
remain separate release gates.

This implementation is not approved for production deployment.

## Next acceptance gates

1. Verify full regression and isolated integration.
2. Validate package-to-installer integration using real artifacts.
3. Add crash/restart fault-injection acceptance.
4. Review race resistance, filesystem durability and recovery.
5. Validate upgrades without losing agent identity or credentials.
6. Run disposable VM acceptance before enabling system installation.
7. Prepare reviewed GitHub pull request and beta release.

No live homelab changes are authorized.
