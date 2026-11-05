#!/usr/bin/env python3
"""Read-only configuration readiness check; never deploys or changes services."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server_settings import DEFAULT_PATH, SettingsError, load


def inspect(path, *, require_network=False):
    settings = load(path)
    checks = []
    def check(name, passed, detail):
        checks.append({'name': name, 'ok': bool(passed), 'detail': detail})
    check('settings_valid', True, 'Settings schema and permissions validated')
    check('public_https_origin', bool(settings['public_url']), 'Required for enrollment/reporting')
    check('network_features_disabled', not (settings['enrollment_enabled'] or settings['reporting_enabled']),
          'Network feature flags are staged, not activated')
    check('tls_external_or_manual', settings['tls_mode'] == 'external',
          'Non-external TLS requires separate certificate/proxy configuration')
    required = ['settings_valid']
    if require_network:
        required.append('public_https_origin')
    return {'ready': all(c['ok'] for c in checks if c['name'] in required),
            'applied': False, 'checks': checks, 'settings': settings}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--path', default=str(DEFAULT_PATH))
    parser.add_argument('--require-network', action='store_true',
                        help='Fail if a public HTTPS origin is not configured')
    args = parser.parse_args(argv)
    try:
        result = inspect(args.path, require_network=args.require_network)
    except (SettingsError, OSError, ValueError) as exc:
        print(json.dumps({'ready': False, 'applied': False, 'error': str(exc)}))
        return 1
    print(json.dumps(result, indent=2))
    return 0 if result['ready'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
