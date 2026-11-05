# Versionary Integrated Beta Installer

## Delivered

A single coordinator connects the complete offline
13-module agent installer to a persistent full-install
recovery marker and post-install verification.

The default operation is preview only.

Execution requires the exact isolated-install
authorization phrase.

Real-system installation remains disabled.

## Preview

```bash id="uvf1rq"
.venv/bin/python \
  installer/versionary-agent-beta-integrated-install.py \
  --root /path/to/isolated-root \
  --distribution installer/dist/versionary-agent-distribution-26l.tar.gz \
  --server https://versionary.example.test \
  --ca-cert /path/to/ca.crt
```

## Authorized isolated installation

Add both:

- `--execute-isolated`
- `--authorize-isolated I_AUTHORIZE_ISOLATED_VERSIONARY_BETA_INSTALL`

Never use a production root.

## Recovery inspection

```bash id="37x9fa"
.venv/bin/python \
  installer/versionary-agent-beta-integrated-install.py \
  --root /path/to/isolated-root \
  --distribution unused \
  --server unused \
  --ca-cert unused \
  --inspect
```

If the installation is interrupted, a recovery marker
remains and blocks another installation.

The marker is never automatically deleted following
an installation error.

Recovery inspection does not delete existing files,
credentials, or agent identity.

## Completion verification

The installer verifies:

- Five expected support/configuration/unit files
- An active release symlink within the release store
- The complete 13-module inventory
- Safe module file types and permissions

No service or timer is activated.

No enrollment occurs.

## Remaining limitations

The installation is multi-stage, not globally atomic.

The recovery marker detects interruption but does
not implement automatic rollback or repair.

A crash can leave a partially installed agent.

The installer does not provide an in-place upgrade.

Real-system deployment remains disabled pending
explicit authorization and disposable VM validation.

## Next milestone

Run complete isolated installation acceptance using
the actual distribution and a generated test CA.

Then prepare a fresh disposable Arch VM trial,
followed by Debian compatibility testing.

Do not modify existing beta VMs or homelab CTs
without explicit approval.
