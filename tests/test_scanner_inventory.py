"""Portable inventory and legacy endpoint regression tests."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import main
from scanner_inventory import InventoryError, LEGACY_TARGETS, load, target, validate


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "inventory.json"
        self.targets = {key: {**value, "host": f"{key}.example.test"}
                        for key, value in LEGACY_TARGETS.items()}
        self.write()

    def write(self):
        self.path.write_text(json.dumps({"version": 1, "targets": self.targets}))
        self.path.chmod(0o600)

    def test_default_targets_preserved_without_opt_in(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(load(), LEGACY_TARGETS)

    def test_explicit_inventory_overrides_all_targets(self):
        with patch.dict(os.environ, {"ARBY_SCANNER_INVENTORY_PATH": str(self.path)}):
            self.assertEqual(target("monitoring")["host"], "monitoring.example.test")

    def test_missing_file_fails_closed(self):
        self.path.unlink()
        with self.assertRaises(InventoryError):
            load(self.path)

    def test_empty_path_fails_closed(self):
        with patch.dict(os.environ, {"ARBY_SCANNER_INVENTORY_PATH": ""}):
            with self.assertRaises(InventoryError):
                load()

    def test_symlink_refused(self):
        copy = self.path.parent / "real.json"
        self.path.rename(copy)
        self.path.symlink_to(copy)
        with self.assertRaises(InventoryError):
            load(self.path)

    def test_public_permissions_refused(self):
        self.path.chmod(0o644)
        with self.assertRaises(InventoryError):
            load(self.path)

    def test_invalid_host_rejected(self):
        for host in ("-bad", "bad..host", "bad host", "evil;command", "user@host",
                     "host/../path", "", "a" * 254):
            with self.subTest(host=host):
                self.targets["proxmox"]["host"] = host
                self.write()
                with self.assertRaises(InventoryError):
                    load(self.path)

    def test_ipv4_ipv6_and_dns_supported(self):
        for host in ("10.20.30.40", "2001:db8::5", "patch.example.test"):
            with self.subTest(host=host):
                self.targets["proxmox"]["host"] = host
                self.write()
                self.assertEqual(load(self.path)["proxmox"]["host"], host)

    def test_missing_target_refused(self):
        self.targets.pop("monitoring")
        self.write()
        with self.assertRaises(InventoryError):
            load(self.path)

    def test_platform_swap_refused(self):
        self.targets["monitoring"]["platform"] = "apt"
        self.write()
        with self.assertRaises(InventoryError):
            load(self.path)

    def test_unknown_field_refused(self):
        self.targets["proxmox"]["command"] = "sh -c dangerous"
        self.write()
        with self.assertRaises(InventoryError):
            load(self.path)

    def test_unsupported_version_refused(self):
        with self.assertRaises(InventoryError):
            validate({"version": 2, "targets": self.targets})

    def test_routes_use_configured_targets_without_ssh(self):
        app = TestClient(main.app)
        self.addCleanup(app.close)
        cases = {
            "proxmox": ("scan_apt_updates", "proxmox"),
            "dns-guard": ("scan_apt_updates", "dns-guard"),
            "docker-nodes": ("scan_apt_updates", "docker-nodes"),
            "monitoring": ("scan_remote_arch_updates", "monitoring"),
            "tailscale": ("scan_remote_arch_updates", "tailscale"),
        }
        with patch.dict(os.environ, {"ARBY_SCANNER_INVENTORY_PATH": str(self.path)}):
            for slug, (func, key) in cases.items():
                with self.subTest(slug=slug), patch.object(main, func, return_value={"status": "success"}) as scan:
                    response = app.get(f"/api/v1/updates/{slug}")
                    self.assertEqual(response.status_code, 200)
                    scan.assert_called_once_with(node=self.targets[key]["node"],
                                                 host=self.targets[key]["host"])

    def test_invalid_inventory_routes_return_503_without_ssh(self):
        self.path.unlink()
        app = TestClient(main.app)
        self.addCleanup(app.close)
        with patch.dict(os.environ, {"ARBY_SCANNER_INVENTORY_PATH": str(self.path)}):
            with patch.object(main, "scan_apt_updates") as apt, patch.object(
                    main, "scan_remote_arch_updates") as arch:
                for slug in LEGACY_TARGETS:
                    with self.subTest(slug=slug):
                        response = app.get(f"/api/v1/updates/{slug}")
                        self.assertEqual(response.status_code, 503)
                apt.assert_not_called()
                arch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
