#!/usr/bin/env bash
# Patch Command: local-only regression checkpoint (no hosted CI).
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
if [[ ! -x .venv/bin/python ]]; then
  echo "[ERROR] Missing .venv. Create it and install requirements first." >&2
  exit 2
fi
PYTHON=.venv/bin/python
LOG="${PATCH_COMMAND_TEST_LOG:-${ARBY_TEST_LOG:-/tmp/arby-tests.log}}"
echo "[Patch Command] Building agent package..."
"$PYTHON" installer/build-agent-package.py
echo "[Patch Command] Running full test suite; output: $LOG"
if "$PYTHON" -m unittest discover -s tests -p 'test_*.py' -q > "$LOG" 2>&1; then
  grep -E '^Ran [0-9]+ tests|^OK$' "$LOG" | tail -n 2
  echo "[Patch Command] PASS"
else
  tail -n 70 "$LOG"
  echo "[Patch Command] FAIL; full log: $LOG" >&2
  exit 1
fi
if [[ "${1:-}" == "--protocol-check" ]]; then
  echo "[Patch Command] Running isolated beta HTTPS acceptance..."
  "$PYTHON" installer/beta-selftest.py --protocol-check
fi
