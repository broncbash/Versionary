# Isolated release switching and restoration

The experimental `installer/release-switch-trial.py` exercises **code release** switching inside a pre-existing, owner-controlled non-root test directory. It requires an existing active agent release and a validated candidate package.

Example, **only after staging a disposable root** with `installer/stage-beta.py`:

```bash
python installer/release-switch-trial.py \
  --root /path/to/disposable-test-root \
  --package installer/dist/arby-patch-agent.tar.gz
```

The exercise verifies the original active release, stages the candidate, activates it, and restores the original release under the install lock. It rejects the real filesystem root, unsafe root permissions, malformed active release links, and invalid package archives.

**Important limitations:** this is not a production installer or a full rollback transaction. It does not back up or restore configuration, credentials, CA trust, service units, or systemd state. An abrupt process termination or power loss may interrupt the restoration sequence; the operator must inspect and recover the isolated root. No live service should use this trial. The existing production installation gate remains disabled.

A complete production-safe workflow still requires durable rollback metadata, crash recovery, independent review, explicit approval, and clean-container acceptance.

## Durable recovery marker (development checkpoint)

The release trial now writes a private, fsynced `.release-recovery.json` marker **before** activating the candidate release. The marker records the previous and candidate code-release hashes. Restoration validates the previous release contents, switches the active symlink back, and removes the marker only after successful restoration. A failed restoration leaves the marker in place for investigation.

`installer/release-recovery.py` provides `read`, `write`, `clear`, and `recover` functions for isolated testing. Recovery must be called while holding the existing installer lock; there is **not yet a supported operator-facing crash-recovery command**. No production rollback, power-loss durability guarantee, service rollback, or recovery of configuration, CA, and credentials is claimed. A crash after restoration but before marker cleanup may leave a marker requiring review.

## Inspect and recover an interrupted isolated trial

For a **pre-existing disposable test root only**, inspect the persistent marker without changing the active release:

```bash
python installer/recover-isolated-release.py --root /path/to/disposable-test-root
```

After reviewing the recorded previous and candidate releases, explicitly restore the prior validated code release:

```bash
python installer/recover-isolated-release.py --root /path/to/disposable-test-root --recover
```

The command takes the installer lock, refuses the live root `/`, rejects unexpected active release targets, and preserves the marker on restoration failure. It requires an existing valid recovery marker. It does **not** restore configuration, CA trust, credentials, systemd units, or service state, and is **not** a production recovery command. Read-only inspection may create the installer lock file if absent.
