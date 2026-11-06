import urllib.request
import time
import ssl
#!/usr/bin/env python3
"""Versionary RC2 disposable-VM installer. Not production approved."""

import argparse
import hashlib
import ipaddress
import json
import os
import pwd
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path


SERVICE = "versionary-server.service"


def run(*command, **kwargs):
    subprocess.run(command, check=True, **kwargs)



def recovery_systemctl(*arguments):
    """Best-effort cleanup without masking the installation failure."""
    try:
        result = subprocess.run(
            ["systemctl", *arguments], check=False
        )
        if result.returncode != 0:
            print(
                "RECOVERY_CLEANUP_ERROR=systemctl "
                + " ".join(arguments)
                + " exited " + str(result.returncode),
                file=sys.stderr,
            )
    except OSError as cleanup_error:
        print(
            "RECOVERY_CLEANUP_ERROR=systemctl "
            + " ".join(arguments) + ": " + str(cleanup_error),
            file=sys.stderr,
        )


def safe_directory(value):
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts:
        raise RuntimeError(f"Unsafe directory: {value}")
    current = Path("/")
    for component in path.parts[1:]:
        current /= component
        if current.is_symlink():
            raise RuntimeError(f"Symlink in directory path: {current}")
        if current.exists() and not current.is_dir():
            raise RuntimeError(f"Non-directory in path: {current}")
    return path


def validate_identity(value):
    if not value or len(value) > 253 or any(
        c in value for c in ("/", "\\", "\x00")
    ):
        raise RuntimeError("Invalid TLS identity")
    try:
        ipaddress.ip_address(value)
        return value
    except ValueError:
        pass
    labels = value.split(".")
    if not all(
        label and len(label) <= 63
        and label[0].isascii() and label[0].isalnum()
        and label[-1].isascii() and label[-1].isalnum()
        and all(c.isascii() and (c.isalnum() or c == "-") for c in label)
        for label in labels
    ):
        raise RuntimeError("Invalid TLS hostname")
    return value


def verify_archive(archive, manifest):
    if archive.is_symlink() or not archive.is_file():
        raise RuntimeError("Archive missing or symlinked")
    if manifest.is_symlink() or not manifest.is_file():
        raise RuntimeError("Manifest missing or symlinked")

    expected = json.loads(manifest.read_text())
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if expected.get("sha256") != digest:
        raise RuntimeError("Archive checksum mismatch")

    with tarfile.open(archive, "r:gz") as tf:
        members = tf.getmembers()
        names = set()
        for member in members:
            name = member.name
            path = Path(name)
            if (
                not member.isfile()
                or path.is_absolute()
                or ".." in path.parts
                or name in names
            ):
                raise RuntimeError(f"Unsafe archive member: {name}")
            names.add(name)

    required = {
        "versionary_https_beta.py",
        "agent/credentials.py",
        "agent_registry.py",
        "installer/generate-certificates.py",
        "requirements-baseline.txt",
    }
    if not required.issubset(names):
        raise RuntimeError("Archive missing required files")

    return digest, len(names)


def service_unit(app, state, identity, bind, port):
    return f"""[Unit]
Description=Versionary RC2 HTTPS Server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=versionary
Group=versionary
WorkingDirectory={app}
Environment=VERSIONARY_STATE_DIR={state}
Environment=VERSIONARY_TLS_IDENTITY={identity}
Environment=VERSIONARY_BIND_ADDRESS={bind}
Environment=VERSIONARY_HTTPS_PORT={port}
Environment=VERSIONARY_BETA_ENROLLMENT=false
Environment=VERSIONARY_BETA_REPORTING=false
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



def verify_https_health(state, identity, bind, port, timeout=30):
    """Verify Versionary HTTPS with CA and hostname validation."""
    import json
    import ipaddress
    import socket
    import ssl
    import time
    import urllib.request

    # Connect locally where possible, without weakening TLS validation.
    if bind in ("127.0.0.1", "::1"):
        connect_host = bind
    else:
        connect_host = bind

    ca_files = [
        p for p in state.rglob("*")
        if p.is_file()
        and "ca" in p.name.lower()
        and p.suffix.lower() in (".crt", ".pem")
    ]

    if len(ca_files) != 1:
        raise RuntimeError(
            "Expected exactly one generated CA certificate"
        )

    context = ssl.create_default_context(cafile=str(ca_files[0]))
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED

    # A custom HTTPSConnection lets us connect to a specific IP while
    # validating the certificate against the configured TLS identity.
    import http.client

    class VerifiedConnection(http.client.HTTPSConnection):
        def connect(self):
            raw = socket.create_connection(
                (connect_host, port),
                timeout=self.timeout,
            )
            try:
                self.sock = self._context.wrap_socket(
                    raw,
                    server_hostname=identity,
                )
            except BaseException:
                raw.close()
                raise

    deadline = time.monotonic() + timeout
    last_error = None

    while time.monotonic() < deadline:
        connection = None
        try:
            connection = VerifiedConnection(
                identity,
                port=port,
                context=context,
                timeout=2,
            )
            connection.request("GET", "/health")
            response = connection.getresponse()
            body = response.read(4096)

            if response.status != 200:
                raise RuntimeError(
                    f"HTTPS health returned HTTP {response.status}"
                )

            payload = json.loads(body)
            if not isinstance(payload, dict):
                raise RuntimeError("Invalid HTTPS health payload")

            if payload.get("status") != "online":
                raise RuntimeError(
                    "HTTPS health status is not online"
                )

            return

        except Exception as exc:
            last_error = exc
            time.sleep(0.25)

        finally:
            if connection is not None:
                connection.close()

    raise RuntimeError(
        "Versionary HTTPS health verification failed: "
        + str(last_error)
    )


def install(args, digest):
    if os.geteuid() != 0:
        raise RuntimeError("Installation requires root")
    # Application files and the venv must be traversable by the unprivileged
    # versionary service user. Keep the separate state directory mode 0700.
    os.umask(0o022)
    if not args.confirm_disposable:
        raise RuntimeError("Use --confirm-disposable on a disposable VM")
    if not Path("/run/systemd/system").is_dir():
        raise RuntimeError("Systemd system manager unavailable")

    app = safe_directory(args.app_dir)
    state = safe_directory(args.state_dir)
    if app == state or app in state.parents or state in app.parents:
        raise RuntimeError("Application and state directories overlap")

    unit = Path("/etc/systemd/system") / SERVICE
    if app.exists() or state.exists() or unit.exists():
        raise RuntimeError("Existing installation detected; refusing overwrite")

    if any(user.pw_name == "versionary" for user in pwd.getpwall()):
        raise RuntimeError("Service account already exists")

    identity = validate_identity(args.tls_identity)
    bind = args.bind_address
    try:
        ipaddress.ip_address(bind)
    except ValueError as exc:
        raise RuntimeError("Bind address must be an IP address") from exc

    if bind not in ("127.0.0.1", "::1") and identity in ("127.0.0.1", "::1"):
        raise RuntimeError("Network binding requires a network TLS identity")

    if bind in ("0.0.0.0", "::"):
        raise RuntimeError("Wildcard binding is disabled for RC2 acceptance")

    if not 1024 <= args.port <= 65535:
        raise RuntimeError("Use an unprivileged HTTPS port")

    for command in ("useradd", "userdel", "systemctl", "runuser"):
        if shutil.which(command) is None:
            raise RuntimeError(f"Missing command: {command}")

    archive = Path(args.archive).absolute()

    created = []
    user_created = False
    service_enabled = False

    try:
        run(
            "useradd", "--system", "--user-group",
            "--home-dir", str(state),
            "--shell", "/usr/bin/nologin",
            "versionary",
        )
        user_created = True

        app.mkdir(parents=True, mode=0o755)
        created.append(app)

        state.mkdir(parents=True, mode=0o700)
        created.append(state)

        with tarfile.open(archive, "r:gz") as tf:
            for member in tf.getmembers():
                destination = app / member.name
                destination.parent.mkdir(parents=True, exist_ok=True)
                with tf.extractfile(member) as source:
                    with destination.open("xb") as output:
                        shutil.copyfileobj(source, output)

        run("chown", "-R", "root:root", str(app))
        run("chmod", "-R", "go-w", str(app))
        run("chown", "versionary:versionary", str(state))
        run("chmod", "700", str(state))

        run(sys.executable, "-m", "venv", str(app / ".venv"))
        run(
            str(app / ".venv/bin/python"), "-m", "pip", "install",
            "--requirement", str(app / "requirements-baseline.txt"),
        )

        env = os.environ.copy()
        env.update({
            "VERSIONARY_STATE_DIR": str(state),
            "VERSIONARY_TLS_IDENTITY": identity,
            "VERSIONARY_BIND_ADDRESS": bind,
            "VERSIONARY_HTTPS_PORT": str(args.port),
        })

        run(
            "runuser", "-u", "versionary", "--",
            str(app / ".venv/bin/python"),
            str(app / "versionary_https_beta.py"),
            "init",
            cwd=app,
            env=env,
        )

        unit.write_text(service_unit(
            app, state, identity, bind, args.port
        ))
        created.append(unit)
        unit.chmod(0o644)

        run("systemctl", "daemon-reload")
        run("systemctl", "enable", "--now", SERVICE)
        service_enabled = True

        run("systemctl", "is-active", "--quiet", SERVICE)

        verify_https_health(
            state, identity, bind, args.port, timeout=30
        )

    except BaseException:
        print("INSTALL_FAILED=RECOVERY_REQUIRED", file=sys.stderr)

        if unit.exists():
            recovery_systemctl("disable", "--now", SERVICE)

        # Preserve application, certificates, state, and diagnostics.
        # A partial installation must be inspected before retrying.
        recovery = state / "INSTALLATION-FAILED.txt"

        if state.is_dir():
            try:
                recovery.write_text(
                    "Versionary RC2 installation failed.\\n"
                    "Application and state were preserved for inspection.\\n"
                    "Do not rerun the installer until the failure is resolved.\\n"
                )
                recovery.chmod(0o600)
            except OSError as marker_error:
                print(
                    "RECOVERY_MARKER_ERROR=" + str(marker_error),
                    file=sys.stderr,
                )

        # Keep the service account so preserved state retains its owner.
        # Do not remove the application or state directories.
        recovery_systemctl("daemon-reload")

        print(
            "RECOVERY_REQUIRED=YES",
            file=sys.stderr,
        )
        raise

    (state / "INSTALLATION-FAILED.txt").unlink(missing_ok=True)
    print("INSTALL=PASS")
    print("ARCHIVE_SHA256=" + digest)
    print("SERVICE=" + SERVICE)
    print("PRODUCTION_APPROVED=NO")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--mode", choices=("dry-run", "install"),
                        default="dry-run")
    parser.add_argument("--confirm-disposable", action="store_true")
    parser.add_argument("--app-dir", default="/opt/versionary")
    parser.add_argument("--state-dir", default="/var/lib/versionary")
    parser.add_argument("--tls-identity", default="127.0.0.1")
    parser.add_argument("--bind-address", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()

    digest, count = verify_archive(
        Path(args.archive).expanduser(),
        Path(args.manifest).expanduser(),
    )

    print("ARCHIVE_FILES=" + str(count))
    print("ARCHIVE_SHA256=" + digest)

    if args.mode == "dry-run":
        print("DRY_RUN=PASS")
        print("INSTALL_EXECUTED=NO")
        return

    install(args, digest)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("STOP: " + str(exc), file=sys.stderr)
        sys.exit(1)
