#!/usr/bin/env python3
"""Read-only display of effective network feature activation gates."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runtime_configuration import effective_flags


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--path', help='Optional settings JSON path')
    args = parser.parse_args(argv)
    print(json.dumps(effective_flags(args.path), indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
