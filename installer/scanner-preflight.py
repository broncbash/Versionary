#!/usr/bin/env python3
"""Read-only diagnostics for portable legacy scanner configuration.

No SSH, filesystem writes, credential disclosure, or live service changes.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scanner_inventory import ENV_PATH as INVENTORY_ENV, InventoryError, load as load_inventory
from scanner_ssh_config import ENV_PATH as SSH_ENV, SSHConfigError, load as load_ssh


def inspect(inventory_path=None, ssh_path=None):
    """Return redacted diagnostics; explicitly supplied paths override env."""
    import os

    result = {"ready": True, "network_contacted": False, "targets": {},
              "inventory": {"configured": inventory_path is not None or INVENTORY_ENV in os.environ,
                            "valid": False},
              "ssh": {"configured": ssh_path is not None or SSH_ENV in os.environ,
                      "valid": False},
              "errors": []}
    try:
        targets = load_inventory(inventory_path)
        result["inventory"]["valid"] = True
        result["targets"] = {name: {"node": target["node"],
                                    "host": target["host"],
                                    "platform": target["platform"]}
                             for name, target in targets.items()}
    except (InventoryError, OSError, ValueError):
        result["errors"].append("Invalid or unavailable scanner inventory")
    try:
        ssh = load_ssh(ssh_path)
        result["ssh"]["valid"] = True
        # No private key path, known-hosts path, or credentials in diagnostics.
        result["ssh"]["username"] = ssh["username"]
        result["ssh"]["strict_host_key_checking"] = True
    except (SSHConfigError, OSError, ValueError):
        result["errors"].append("Invalid or unavailable scanner SSH configuration")
    result["ready"] = not result["errors"]
    if not result["ready"]:
        result["targets"] = {}
    return result


def main():
    parser = argparse.ArgumentParser(description="Read-only scanner configuration preflight")
    parser.add_argument("--inventory-path", help="Private inventory JSON file")
    parser.add_argument("--ssh-path", help="Private SSH transport JSON file")
    args = parser.parse_args()
    result = inspect(args.inventory_path, args.ssh_path)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ready"] else 1


if __name__ == "__main__":
    sys.exit(main())
