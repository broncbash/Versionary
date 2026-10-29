"""Validated inventory for legacy read-only SSH scanners.

No network discovery, writes, or automatic configuration. Existing legacy
targets are retained only when no inventory path has been configured.
"""
import ipaddress
import json
import os
import re
import stat
from pathlib import Path

ENV_PATH = "ARBY_SCANNER_INVENTORY_PATH"
LEGACY_TARGETS = {
    "proxmox": {"node": "PVE CORE", "host": "192.168.86.5", "platform": "apt"},
    "dns-guard": {"node": "DNS GUARD", "host": "192.168.86.10", "platform": "apt"},
    "docker-nodes": {"node": "DOCKER NODES", "host": "192.168.86.12", "platform": "apt"},
    "monitoring": {"node": "MONITORING", "host": "192.168.86.13", "platform": "arch"},
    "tailscale": {"node": "TAILSCALE", "host": "192.168.86.14", "platform": "arch"},
}
_HOST = re.compile(r"(?=.{1,253}$)[a-zA-Z0-9](?:[a-zA-Z0-9.-]*[a-zA-Z0-9])?\Z")
_NODE = re.compile(r"[A-Za-z0-9 _.-]{1,64}\Z")


class InventoryError(ValueError):
    pass


def _host(value):
    if not isinstance(value, str) or not value or len(value) > 253:
        raise InventoryError("Invalid scanner hostname")
    try:
        ipaddress.ip_address(value)
        return value
    except ValueError:
        pass
    if (not _HOST.fullmatch(value) or ".." in value or
            any(not label or len(label) > 63 or label.startswith("-") or
                label.endswith("-") for label in value.split("."))):
        raise InventoryError("Invalid scanner hostname")
    return value


def validate(data):
    if not isinstance(data, dict) or set(data) != {"version", "targets"}:
        raise InventoryError("Inventory requires version and targets")
    if type(data["version"]) is not int or data["version"] != 1:
        raise InventoryError("Unsupported inventory version")
    targets = data["targets"]
    if not isinstance(targets, dict) or set(targets) != set(LEGACY_TARGETS):
        raise InventoryError("Inventory must declare all legacy scanner targets")
    validated = {}
    for key, item in targets.items():
        if not isinstance(item, dict) or set(item) != {"node", "host", "platform"}:
            raise InventoryError("Invalid scanner target fields")
        if item["platform"] != LEGACY_TARGETS[key]["platform"]:
            raise InventoryError("Scanner platform cannot be changed")
        if not isinstance(item["node"], str) or not _NODE.fullmatch(item["node"]):
            raise InventoryError("Invalid scanner node label")
        validated[key] = {"node": item["node"], "host": _host(item["host"]),
                          "platform": item["platform"]}
    return validated


def load(path=None):
    selected = path if path is not None else os.environ.get(ENV_PATH)
    if selected is None:
        return {key: dict(value) for key, value in LEGACY_TARGETS.items()}
    if not isinstance(selected, (str, os.PathLike)) or not str(selected).strip():
        raise InventoryError("Inventory path must be nonempty")
    path = Path(selected)
    try:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
            raise InventoryError("Inventory must be a private regular file")
        return validate(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError) as exc:
        raise InventoryError("Invalid or inaccessible scanner inventory") from exc


def target(key):
    if key not in LEGACY_TARGETS:
        raise InventoryError("Unknown scanner target")
    return load()[key]
