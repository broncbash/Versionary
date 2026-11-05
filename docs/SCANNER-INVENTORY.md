# Portable legacy scanner inventory (development)

The five existing read-only SSH update endpoints now resolve their targets
through `scanner_inventory.py`. This does **not** install patches, discover
hosts, modify SSH credentials, or enable V2 enrollment.

## Compatibility and migration

When `ARBY_SCANNER_INVENTORY_PATH` is **unset**, the development code retains
the original legacy homelab targets for compatibility. This fallback is a
migration bridge, **not** a portable production default.

When `ARBY_SCANNER_INVENTORY_PATH` is set, the configured JSON must exist,
be a regular private file (no group/other permissions), and validate fully.
An invalid, missing, or symlinked file fails closed: all five remote update
routes return HTTP 503 and **do not initiate SSH**. An empty path is invalid.
No automatic fallback to homelab addresses occurs in this case.

## Inventory example

Create a private file such as `/etc/patch-command/scanners.json`:

```json
{
  "version": 1,
  "targets": {
    "proxmox": {"node": "PVE CORE", "host": "pve.example.test", "platform": "apt"},
    "dns-guard": {"node": "DNS GUARD", "host": "dns.example.test", "platform": "apt"},
    "docker-nodes": {"node": "DOCKER NODES", "host": "docker.example.test", "platform": "apt"},
    "monitoring": {"node": "MONITORING", "host": "monitor.example.test", "platform": "arch"},
    "tailscale": {"node": "TAILSCALE", "host": "router.example.test", "platform": "arch"}
  }
}
```

Use `chmod 600 /etc/patch-command/scanners.json` and set
`ARBY_SCANNER_INVENTORY_PATH=/etc/patch-command/scanners.json` in the
**development service environment only**. Do not change the running CT104
service as part of this milestone.

All five keys are currently required because they map to the existing
legacy routes. Their platform types are fixed to avoid inadvertently
executing the wrong scanner. Future versions should support user-defined
targets, dynamically generated routes, and authenticated GUI/CLI management.

The SSH identity and known-hosts locations are still legacy-specific.
This milestone configures *targets*, not credentials or transport.

## Verification

```sh
python -m unittest tests.test_scanner_inventory -v
python -m unittest discover -s tests -p 'test_*.py' -q
```

No merge or production deployment is authorized by this document.
