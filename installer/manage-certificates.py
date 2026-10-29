#!/usr/bin/env python3
"""Offline TLS certificate inspection/import; never changes the running proxy."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from certificate_management import CertificateError, validate_files, install_pair, inspect_certificate
from certificate_renewal import RenewalError, renew


def main():
    parser = argparse.ArgumentParser(description='Validate or safely import server TLS certificate and key')
    parser.add_argument('action', choices=('check', 'import', 'inspect', 'renew'))
    parser.add_argument('--cert', required=True)
    parser.add_argument('--key', help='Required for check/import; not for inspect')
    parser.add_argument('--hostname', help='Required for check/import; optional for inspect')
    parser.add_argument('--warning-days', type=int, default=30, help='Expiry warning threshold for inspect')
    parser.add_argument('--destination', help='Existing private (0700) directory; required for import')
    parser.add_argument('--ca-cert', help='Issuer CA certificate for renew')
    parser.add_argument('--ca-key', help='Private issuer CA key for renew')
    parser.add_argument('--days', type=int, default=365, help='Renewed leaf lifetime')
    args = parser.parse_args()
    try:
        if args.action in ('check', 'import') and (not args.key or not args.hostname):
            parser.error('--key and --hostname are required for check/import')
        if args.action == 'renew':
            if not all((args.ca_cert, args.ca_key, args.hostname, args.destination)):
                parser.error('renew requires --ca-cert --ca-key --hostname --destination')
            result = renew(args.ca_cert, args.ca_key, args.hostname, args.destination, args.days)
        elif args.action == 'inspect':
            result = inspect_certificate(args.cert, args.hostname, args.warning_days)
        elif args.action == 'import':
            if not args.destination:
                parser.error('--destination required for import')
            result = install_pair(args.cert, args.key, args.hostname, args.destination)
        else:
            result = validate_files(args.cert, args.key, args.hostname)
        print(json.dumps({'valid': result.get('status') == 'valid' if args.action == 'inspect' else True, 'applied': False, 'certificate': result}, indent=2))
    except (CertificateError, RenewalError, OSError, ValueError) as exc:
        print(f'[ERROR] {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
