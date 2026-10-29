#!/usr/bin/env python3
"""Offline TLS certificate inspection/import; never changes the running proxy."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from certificate_management import CertificateError, validate_files, install_pair


def main():
    parser = argparse.ArgumentParser(description='Validate or safely import server TLS certificate and key')
    parser.add_argument('action', choices=('check', 'import'))
    parser.add_argument('--cert', required=True)
    parser.add_argument('--key', required=True)
    parser.add_argument('--hostname', required=True)
    parser.add_argument('--destination', help='Existing private (0700) directory; required for import')
    args = parser.parse_args()
    try:
        if args.action == 'import':
            if not args.destination:
                parser.error('--destination required for import')
            result = install_pair(args.cert, args.key, args.hostname, args.destination)
        else:
            result = validate_files(args.cert, args.key, args.hostname)
        print(json.dumps({'valid': True, 'applied': False, 'certificate': result}, indent=2))
    except (CertificateError, OSError) as exc:
        print(f'[ERROR] {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
