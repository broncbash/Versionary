"""VERSIONARY AGENT command-line application."""

import argparse
import json
import socket
import sys

from agent.versionary_agent import detect_platform, scan
from agent.credentials import CredentialError, load_credential
from agent.enrollment_client import register_v2, complete_v2
from agent.heartbeat import HeartbeatError, send_heartbeat
from agent.identity import get_or_create_identity
from agent.registration import RegistrationError, register_agent
from agent.reporting import ReportingError, send_report


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="versionary-agent",
        description="VERSIONARY AGENT — observer-only monitoring",
    )

    parser.add_argument(
        "command",
        choices=("status", "scan", "register", "heartbeat", "report", "register-v2", "enroll-v2"),
    )

    args = parser.parse_args(argv)

    try:
        if args.command == "scan":
            result = scan()
            print(json.dumps(result, indent=2))
            return 0 if result["status"] == "success" else 1

        platform = detect_platform()

        identity = get_or_create_identity(
            hostname=socket.gethostname(),
            platform=platform,
        )

        if args.command == "status":
            try:
                load_credential()
                credential_status = "provisioned"
            except CredentialError:
                credential_status = "not provisioned"

            print(json.dumps({
                "agent_id": identity["agent_id"],
                "hostname": identity["hostname"],
                "platform": identity["platform"],
                "credential": credential_status,
            }, indent=2))
            return 0

        if args.command == "register":
            result = register_agent(identity)

        elif args.command == "register-v2":
            result = register_v2(identity)

        elif args.command == "enroll-v2":
            result = complete_v2(identity)

        elif args.command == "heartbeat":
            token = load_credential()
            result = send_heartbeat(identity, token)

        elif args.command == "report":
            token = load_credential()
            result = send_report(identity, token, scan())

        else:
            parser.error("Unknown command")

        print(json.dumps(result, indent=2))
        return 0

    except (
        RuntimeError,
        OSError,
        ValueError,
        KeyError,
    ) as exc:
        print(
            f"VERSIONARY AGENT: {exc}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
