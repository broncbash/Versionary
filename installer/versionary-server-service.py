#!/usr/bin/env python3
"""Generate a non-deploying Versionary server systemd service preview."""

import argparse
import os
import stat
from pathlib import Path


def validate_path(value, label):
    path = Path(value).expanduser()

    if not path.is_absolute():
        raise ValueError(f"{label} must be absolute")

    if ".." in path.parts:
        raise ValueError(f"{label} must not contain '..'")

    current = Path("/")

    for component in path.parts[1:]:
        current = current / component

        if current.is_symlink():
            raise ValueError(f"{label} contains a symlink: {current}")

        if current.exists() and not current.is_dir():
            raise ValueError(f"{label} contains a non-directory: {current}")

    return path


def generate(app_dir, state_dir, user):
    app = validate_path(app_dir, "Application directory")
    state = validate_path(state_dir, "State directory")

    if app == state or app in state.parents or state in app.parents:
        raise ValueError("Application and state directories must be separate")

    if not user or not all(c.isalnum() or c in "_-" for c in user):
        raise ValueError("Invalid service account")

    return f"""[Unit]
Description=Versionary Isolated HTTPS Beta Server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User={user}
Group={user}
WorkingDirectory={app}
Environment=VERSIONARY_STATE_DIR={state}
Environment=VERSIONARY_BETA_REPORTING=false
Environment=VERSIONARY_BETA_ENROLLMENT=false
Environment=VERSIONARY_DISTRIBUTION_ENABLED=false
ExecStart={app}/.venv/bin/python {app}/versionary_https_beta.py serve
Restart=on-failure
RestartSec=5
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths={state}

[Install]
WantedBy=multi-user.target
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-dir", default="/opt/versionary")
    parser.add_argument("--state-dir", default="/var/lib/versionary")
    parser.add_argument("--user", default="versionary")
    parser.add_argument("--output")
    args = parser.parse_args()

    unit = generate(args.app_dir, args.state_dir, args.user)

    if args.output:
        output = Path(args.output)
        if output.exists() or output.is_symlink():
            raise SystemExit("Refusing to overwrite existing output")
        output.write_text(unit)
        print(f"SERVICE_PREVIEW={output}")
    else:
        print(unit)


if __name__ == "__main__":
    main()
