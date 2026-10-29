#!/usr/bin/env bash
# ARBY PATCH COMMAND: local-only regression checkpoint (no GitHub Actions).
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
if [[ ! -x .venv/bin/python ]]; then
  echo "[ERROR] Missing .venv. Create it and install requirements first." >&2
  exit 2
fi
PYTHON=.venv/bin/python
LOG="${ARBY_TEST_LOG:-/tmp/arby-tests.log}"
echo "[ARBY] Building agent package..."
"$PYTHON" installer/build-agent-package.py
echo "[ARBY] Running full test suite; output: $LOG"
if "$PYTHON" -m unittest discover -s tests -p 'test_*.py' -q > "$LOG" 2>&1; then
  grep -E '^Ran [0-9]+ tests|^OK$' "$LOG" | tail -n 2
  echo "[ARBY] PASS"
else
  tail -n 70 "$LOG"
  echo "[ARBY] FAIL; full log: $LOG" >&2
  exit 1
fi
if [[ "${1:-}" == "--protocol-check" ]]; then
  echo "[ARBY] Running isolated beta HTTPS acceptance..."
  "$PYTHON" installer/beta-selftest.py --protocol-check
fi
