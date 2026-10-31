"""Opt-in, unprivileged Versionary agent CLI; no service installation."""
import argparse
import functools
import json
import os
import socket
import stat
import sys
from pathlib import Path

from agent.config import validate_server
from agent.credentials import load_credential, prepare_directory, validate_directory
from agent.enrollment_client import register_v2, complete_v2
from agent.enrollment_http import post_json
from agent.heartbeat import send_heartbeat
from agent.identity import get_or_create_identity, load_identity
from agent.reporting import send_report
from agent.versionary_agent import detect_platform, scan

DEFAULT_STATE = Path.home() / ".local" / "state" / "versionary-agent"


def state_paths(root):
    root = Path(root).expanduser().absolute()
    return {
        "root": root,
        "config": root / "config.json",
        "identity": root / "identity.json",
        "key": root / "enrollment-key.json",
        "journal": root / "enrollment-pending.json",
        "credential": root / "credential.json",
    }


def read_config(paths):
    validate_directory(paths["root"])
    path = paths["config"]
    if path.is_symlink():
        raise RuntimeError("Configuration symlinks are forbidden")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o600:
        raise RuntimeError("Configuration must be an owned private regular file (0600)")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or set(data) != {"server", "ca_cert"}:
        raise RuntimeError("Invalid agent configuration")
    server = validate_server(data["server"])
    ca = Path(data["ca_cert"])
    if not ca.is_absolute() or ca.is_symlink() or not ca.is_file():
        raise RuntimeError(
            "CA certificate must be an existing regular file, not a symlink"
        )
    return server, ca


def setup(paths, server, ca_cert):
    server = validate_server(server)
    ca = Path(ca_cert).expanduser().absolute()
    if not ca.is_file() or ca.is_symlink():
        raise RuntimeError("CA certificate must be an existing regular file, not a symlink")
    prepare_directory(paths["root"])
    # Exclusive creation avoids silently replacing trust anchors.
    fd = os.open(paths["config"], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump({"server": server, "ca_cert": str(ca)}, stream)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        paths["config"].unlink(missing_ok=True)
        raise
    return server


def identity_for(paths):
    return get_or_create_identity(
        socket.gethostname(), detect_platform(), path=paths["identity"]
    )


def existing_identity(paths):
    validate_directory(paths["root"])
    validate_identity_file(paths["identity"])
    identity = load_identity(paths["identity"])
    if identity is None:
        raise RuntimeError("No identity yet; run register first")
    return identity


def validate_identity_file(path):
    """Reject identity substitution and unsafe permissions."""
    if path.is_symlink():
        raise RuntimeError("Agent identity symlinks are forbidden")

    info = path.stat()

    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_uid != os.geteuid()
        or stat.S_IMODE(info.st_mode) != 0o600
    ):
        raise RuntimeError(
            "Agent identity must be an owned private file (0600)"
        )


def run(args):
    paths = state_paths(args.state_dir)
    if args.command == "setup":
        server = args.server
        ca_cert = args.ca_cert
        if args.interactive:
            server = server or input("Versionary HTTPS server URL: ").strip()
            ca_cert = ca_cert or input("CA certificate path: ").strip()
        if not server or not ca_cert:
            raise RuntimeError("setup requires --server and --ca-cert (or --interactive)")
        print("Configured:", setup(paths, server, ca_cert))
        print("No agent registered and no background service installed.")
        return 0

    server, ca = read_config(paths)
    if args.command == "status":
        if paths["identity"].exists() or paths["identity"].is_symlink():
            validate_identity_file(paths["identity"])
        identity = load_identity(paths["identity"])
        print("Server:", server)
        print("Agent ID:", identity["agent_id"] if identity else "not registered")
        try:
            load_credential(paths["credential"])
            print("Local credential: provisioned (server authorization not checked)")
        except FileNotFoundError:
            print("Local credential: missing")
        except RuntimeError as exc:
            if "has not been provisioned" in str(exc):
                print("Local credential: missing")
            else:
                raise
        return 0

    if args.command == "register":
        if paths["identity"].exists() or paths["identity"].is_symlink():
            validate_identity_file(paths["identity"])
        identity = identity_for(paths)
        post = functools.partial(post_json, server=server, ca_cert=ca)
        response = register_v2(identity, key_path=paths["key"], post=post)
        print("Registration:", response["status"])
        print("Agent ID:", identity["agent_id"])
        print("Administrator approval is required before enroll.")
        return 0

    identity = existing_identity(paths)
    if args.command == "enroll":
        post = functools.partial(post_json, server=server, ca_cert=ca)
        response = complete_v2(
            identity, key_path=paths["key"], journal_path=paths["journal"],
            credential_path=paths["credential"], post=post,
        )
        print("Enrollment:", response["status"])
        return 0

    token = load_credential(paths["credential"])
    if args.command == "heartbeat":
        result = send_heartbeat(identity, token, server=server, ca_cert=ca)
        print("Heartbeat:", result.get("status", "acknowledged"))
        return 0

    if args.command == "report":
        report = scan()
        result = send_report(identity, token, report, server=server, ca_cert=ca)
        print("Report:", result["status"])
        print("Scan status:", report["status"])
        print("Packages:", len(report["packages"]))
        return 0 if report["status"] == "success" else 1

    raise RuntimeError("Unknown command")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Versionary agent: manual secure enrollment and reporting")
    parser.add_argument("--state-dir", default=str(DEFAULT_STATE),
                        help="Private agent state directory (default: ~/.local/state/versionary-agent)")
    sub = parser.add_subparsers(dest="command", required=True)
    setup_parser = sub.add_parser("setup", help="Save HTTPS origin and CA path; never overwrite")
    setup_parser.add_argument("--server")
    setup_parser.add_argument("--ca-cert")
    setup_parser.add_argument("--interactive", action="store_true")
    for name in ("status", "register", "enroll", "heartbeat", "report"):
        sub.add_parser(name)
    args = parser.parse_args(argv)
    try:
        return run(args)
    except (RuntimeError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
