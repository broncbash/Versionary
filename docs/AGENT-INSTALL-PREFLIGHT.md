# Agent installation preflight (development only)

The new `installer/agent-preflight.py` checks installation readiness without
installing packages, writing configuration, contacting a server, starting a
service, or enabling timers. Production `--install` remains disabled.

Run from a checkout after building the package:

```sh
python3 installer/build-agent-package.py
python3 installer/agent-preflight.py \
  --server https://patch.example.test:8443 \
  --ca-cert /path/to/trusted-ca.crt
```

The JSON report contains `ready`, `changes_made: false`,
`production_install_enabled: false`, the detected platform, and checks for:
supported Arch/Debian OS, Python, systemctl, cryptography, a read-only package
scanner, valid HTTPS origin, readable PEM CA, and a validated agent archive.
The command exits 0 when all checks pass and 1 otherwise.

A successful preflight **does not prove** that a server is reachable, that
the CA is trusted by the target server, or that the service can be installed.
It is not permission to deploy. The PEM check is a lightweight file-format
readiness check, not full X.509 chain validation; proper TLS handshake and
trust-chain tests remain release blockers.

The isolated installation smoke test remains:

```sh
bash installer/install-agent.sh --test-install --server https://patch.example.test
```

No production installation, enrollment, automatic patching, or reboot is
enabled by these development commands.
