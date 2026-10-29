# Isolated agent installation integrity audit

The test-only installer now invokes `installer/audit-test-install.py`
after staging an agent release, trusted CA, configuration, systemd service,
and timer. This is a **read-only verification step**, not a production installer.

The audit compares installed agent source bytes with the validated archive,
checks that the active symlink targets the matching content-addressed release,
verifies private persistent-state directory permissions, and checks the
presence and basic file types of the configuration, CA, and systemd units.

Run the full isolated test from a checkout with a built package:

```sh
python3 installer/build-agent-package.py
bash installer/install-agent.sh --test-install
```

For an existing disposable test root, use:

```sh
python3 installer/audit-test-install.py \
  --root /path/to/isolated-root \
  --package installer/dist/arby-patch-agent.tar.gz
```

The audit returns JSON and exits 0 only if its checks pass. It refuses the
real filesystem root `/`, does not contact remote servers, and does not
enable or start systemd units. It is a post-install integrity *smoke test*,
not a full filesystem adversarial security audit or an end-to-end TLS test.
The production `--install` path remains disabled.
