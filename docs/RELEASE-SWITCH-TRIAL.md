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
