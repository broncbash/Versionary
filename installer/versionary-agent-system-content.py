#!/usr/bin/env python3
"""Content-aware checks for existing Versionary system installation files."""

import importlib.util
import json
import os
import stat
from pathlib import Path


HERE = Path(__file__).resolve().parent


def load_helper(filename, name):
    spec = importlib.util.spec_from_file_location(
        name,
        HERE / filename,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expected_payloads(distribution, server, ca_cert):
    cli = load_helper(
        "install-agent-cli.py",
        "versionary_content_cli",
    )
    config = load_helper(
        "../agent/config.py",
        "versionary_content_config",
    )
    ca = load_helper(
        "install-ca.py",
        "versionary_content_ca",
    )

    cli_payload = cli.verified_cli(distribution)
    validated = config.validate_config({
        "server": server,
        "ca_cert": "/etc/versionary-agent/ca.crt",
    })

    ca_payload = Path(ca_cert).read_bytes()
    ca.validate_ca(ca_payload)

    config_payload = (
        json.dumps(validated, indent=2) + "\n"
    ).encode()

    service = (
        HERE / "systemd/versionary-agent.service"
    ).read_bytes()

    timer = (
        HERE / "systemd/versionary-agent.timer"
    ).read_bytes()

    return {
        "opt/versionary-agent/versionary_agent_cli.py":
            cli_payload,
        "etc/versionary-agent/config.json":
            config_payload,
        "etc/versionary-agent/ca.crt":
            ca_payload,
        "etc/systemd/system/versionary-agent.service":
            service,
        "etc/systemd/system/versionary-agent.timer":
            timer,
    }


def inspect_existing(root, payloads, expected_uid=None):
    root = Path(root)

    if expected_uid is None:
        expected_uid = os.geteuid()

    results = {}

    for relative, expected in payloads.items():
        target = root / relative

        try:
            info = target.lstat()
        except FileNotFoundError:
            results[relative] = "absent"
            continue

        if not stat.S_ISREG(info.st_mode):
            raise ValueError(
                f"Unsafe existing installation file: {relative}"
            )

        if (
            info.st_uid != expected_uid
            or info.st_nlink != 1
            or info.st_mode & 0o022
        ):
            raise ValueError(
                f"Unsafe existing installation file: {relative}"
            )

        if info.st_size != len(expected):
            raise ValueError(
                f"Existing installation file differs: {relative}"
            )

        if target.read_bytes() != expected:
            raise ValueError(
                f"Existing installation file differs: {relative}"
            )

        results[relative] = "identical"

    return results
