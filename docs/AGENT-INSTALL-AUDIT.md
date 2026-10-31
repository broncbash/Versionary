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
  --package installer/dist/versionary-agent.tar.gz
```

The audit returns JSON and exits 0 only if its checks pass. It refuses the
real filesystem root `/`, does not contact remote servers, and does not
enable or start systemd units. It is a post-install integrity *smoke test*,
not a full filesystem adversarial security audit or an end-to-end TLS test.
The production `--install` path remains disabled.

## Additional filesystem tampering checks

The audit rejects symlinked or hardlinked installed source files, configuration,
CA certificates, and systemd units. It verifies file ownership and rejects
unsafe group/other-writable files. Python's normal `__pycache__` directory
is permitted, but unexpected entries, non-regular bytecode files, symlinks,
and hardlinks in that directory are rejected. These checks are regression
coverage for isolated test roots, **not** a guarantee against concurrent
filesystem races or a substitute for production deployment security review.

## Repeat installation smoke test

The `--test-install` workflow now runs the isolated installation twice. Before
its second pass, it records the active release target and SHA-256 hashes of
the installed CA, configuration, service, and timer. It reruns the file, CA,
configuration, and systemd installers and requires all recorded values to
remain unchanged. A second read-only integrity audit must also pass.

This verifies repeatability for an identical package and configuration. It
does not test upgrades to a different package, CA rotation, enrollment,
production installation, or the running systemd service.

## Failed reinstall and activation regression coverage

The release transaction tests also verify that rejected source tampering,
unsafe Python bytecode caches, and simulated activation failures do not
switch the active release symlink. This protects the currently selected
release when staging or activation fails. A rejected reinstall can still
leave pre-existing tampered files in place; these tests do **not** claim
automatic repair or rollback of all installer side effects.

## Configuration and CA conflict regression tests

Additional tests exercise rejected server-origin changes, CA path changes,
symlinked configuration files, replacement CA certificates, mismatched CA
fingerprints, and hardlinked installed CA certificates. In each rejected
case, the existing configuration or CA bytes must remain unchanged. This
is not an automatic certificate rotation or migration workflow; intentional
trust changes will require a separate administrator-approved procedure.
