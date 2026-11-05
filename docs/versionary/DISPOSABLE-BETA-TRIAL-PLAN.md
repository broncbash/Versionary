# Versionary — Disposable Beta Installation Trial

## Status

PLANNED — NOT AUTHORIZED

This document defines the next controlled-beta acceptance
trial. It does not authorize deployment or enable the
real-system installer.

## Verified baseline

- Feature branch: feature/versionary-agent-rename
- Verified commit: 993b214
- Local regression: 1,650 tests passed; 1 skipped
- Isolated fresh agent installation: passed
- Distribution: versionary-agent-distribution-26l.tar.gz
- Installed modules: 13
- CLI, CA, configuration and systemd definitions: verified
- Service activation: none
- Enrollment: none
- Reinstallation over existing state: refused

## Current blockers

The real-system installer deliberately raises
InstallationNotImplemented.

The isolated transaction engine is not authorized for
real-system installation.

The complete isolated installer is multi-stage and not
globally atomic. An interrupted installation can leave
partial state requiring manual review.

Passing isolated tests does not establish readiness for
real-system deployment.

## Trial target

Use a NEW disposable Linux virtual machine.

Do not reuse or modify the existing beta server or agents
without separate explicit approval.

Do not modify CT 102 or CT 104.

Record before authorization:

- VM name and operating system
- VM identifier and network address
- Confirmation that it is disposable
- Snapshot identifier and restoration procedure
- Installation package checksum
- Server HTTPS endpoint and CA certificate
- Operator and trial date

No target is currently approved.

## Proposed acceptance sequence

1. Create and identify a disposable test VM.
2. Verify snapshot and rollback capability.
3. Confirm supported Linux environment.
4. Verify distribution integrity and CA trust.
5. Run read-only preflight and conflict checks.
6. Review exact installer changes and authorization.
7. Obtain explicit approval for that VM.
8. Implement and test any required real-system
   installation functionality separately.
9. Execute only the approved fresh-install trial.
10. Verify installed files, ownership and permissions.
11. Verify service and timer definitions.
12. Verify no unexpected service activation.
13. Verify no automatic patching or rebooting.
14. Test enrollment only under separate approval.
15. Record evidence and restore the disposable VM
    when the trial is complete.

## Stop conditions

Stop immediately for:

- Existing Versionary identity or credentials
- Existing application installation or unknown state
- Pending installation or recovery journal
- Unsafe symlinks, hardlinks or writable directories
- Invalid distribution or CA certificate
- Unexpected service activation
- Unapproved filesystem changes
- Missing or unverified rollback capability

Never automatically delete unknown existing state.

## Recovery

The current isolated installation is not globally atomic.

An interrupted installation requires inspection of
application, configuration, service and state paths.

Do not retry installation or remove partial data until
the operator has reviewed the state.

A snapshot restore is the preferred disposable-VM
recovery mechanism.

## Required evidence

Capture:

- Exact approved target
- Snapshot identifier
- Package digest
- Preflight results
- Installation result
- Installed module count
- File permissions and ownership
- Service and timer status
- Enrollment status
- Recovery/rollback result
- Any failures and corrective actions

## Release restrictions

This plan does not approve:

- Real-system installation
- Production deployment
- Hosted CI
- GitHub merge
- Release publication
- Tags
- In-place upgrades
- Automatic patching
- Automatic rebooting
- Changes to existing beta VMs or homelab containers

## Next decision

Review the plan and identify a new disposable VM.

Real-system installation requires separate implementation,
verification and explicit target-specific authorization.
