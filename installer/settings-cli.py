#!/usr/bin/env python3
"""CLI interface to the same validated server settings backend as the admin API."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server_settings import DEFAULT_PATH, SettingsError, load, save

parser = argparse.ArgumentParser(description='ARBY server settings (staged, not applied to running services)')
parser.add_argument('--path', default=str(DEFAULT_PATH))
sub = parser.add_subparsers(dest='action', required=True)
sub.add_parser('show')
change = sub.add_parser('set')
change.add_argument('key', choices=['public_url', 'enrollment_enabled', 'reporting_enabled', 'scan_interval_minutes', 'appearance', 'tls_mode'])
change.add_argument('value')
args = parser.parse_args()
try:
    if args.action == 'show':
        result = load(args.path)
    else:
        value = args.value
        if args.key in ('enrollment_enabled', 'reporting_enabled'):
            if value.lower() not in ('true', 'false'):
                raise SettingsError('Boolean must be true or false')
            value = value.lower() == 'true'
        elif args.key == 'scan_interval_minutes':
            value = int(value)
        elif args.key == 'public_url' and value.lower() == 'null':
            value = None
        result = save({args.key: value}, args.path)
    print(json.dumps(result, indent=2))
except (SettingsError, OSError, ValueError) as exc:
    print(f'[ERROR] {exc}', file=sys.stderr)
    sys.exit(1)
