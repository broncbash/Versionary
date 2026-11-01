#!/usr/bin/env python3
"""Guided Versionary agent first run; manual, opt-in, no daemon installation."""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import versionary_agent_cli as cli

MENU = {
    "1": ("Configure trusted HTTPS connection", "setup"),
    "2": ("Check agent status", "status"),
    "3": ("Request agent registration", "register"),
    "4": ("Complete enrollment after admin approval", "enroll"),
    "5": ("Send heartbeat", "heartbeat"),
    "6": ("Send update report (read-only scan)", "report"),
}

def main(argv=None):
    parser = argparse.ArgumentParser(description="Versionary Beta 0.9 guided agent first run")
    parser.add_argument("--state-dir", default=str(cli.DEFAULT_STATE))
    parser.add_argument("--guide", action="store_true", help="Print workflow without making changes")
    args = parser.parse_args(argv)
    print("VERSIONARY BETA 0.9 — AGENT FIRST RUN")
    print("Observer only. No patch installation, service activation, or reboot.")
    print("Server must be running with enrollment v2 and reporting explicitly enabled.")
    print("Administrator approval is required after registration.")
    print("State directory:", args.state_dir)
    if args.guide:
        for key, (label, _) in MENU.items():
            print(f"  {key}. {label}")
        print("  0. Exit")
        return 0
    if not sys.stdin.isatty():
        print("[ERROR] Interactive terminal required; use --guide for read-only help.", file=sys.stderr)
        return 1
    while True:
        print()
        for key, (label, _) in MENU.items():
            print(f"  {key}. {label}")
        print("  0. Exit")
        choice = input("Choose: ").strip()
        if choice == "0":
            return 0
        if choice not in MENU:
            print("Unknown choice")
            continue
        command = MENU[choice][1]
        argv2 = ["--state-dir", args.state_dir, command]
        if command == "setup":
            server = input("HTTPS server origin (https://host:port): ").strip()
            ca = input("Trusted CA certificate file: ").strip()
            argv2 += ["--server", server, "--ca-cert", ca]
        if command in ("register", "enroll", "heartbeat", "report"):
            answer = input(f"Proceed with {command}? [y/N]: ").strip().lower()
            if answer != "y":
                print("Cancelled")
                continue
        result = cli.main(argv2)
        if result:
            print("[ERROR] Action failed. Check server configuration, approval, and TLS trust.")
        elif command == "register":
            print("NEXT: Administrator must approve the pending agent before enrollment.")
        elif command == "enroll":
            print("NEXT: Send a heartbeat and read-only update report.")

if __name__ == "__main__":
    raise SystemExit(main())
