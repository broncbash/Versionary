#!/usr/bin/env bash
set -euo pipefail

# ARBY PATCH AGENT installer
# Initial version: dry-run only.

MODE="dry-run"
SERVER=""
CA_SOURCE=""
INTERACTIVE=0

while (( $# )); do
    case "$1" in
        --install) MODE="install" ;;
        --test-install) MODE="test-install" ;;
        --server)
            [[ $# -ge 2 ]] || { echo "Missing --server value" >&2; exit 2; }
            SERVER="$2"; shift ;;
        --ca-cert)
            [[ $# -ge 2 ]] || { echo "Missing --ca-cert value" >&2; exit 2; }
            CA_SOURCE="$2"; shift ;;
        --interactive) INTERACTIVE=1 ;;
        --help|-h)
            echo "Usage: $0 [--test-install|--install] [--server HTTPS_URL] [--ca-cert PEM_FILE] [--interactive]"
            echo "Production installation remains disabled."
            exit 0 ;;
        *) echo "Unknown option: $1" >&2; exit 2 ;;
    esac
    shift
done

if (( INTERACTIVE )); then
    [[ -t 0 ]] || { echo "Interactive mode requires a terminal" >&2; exit 2; }
    if [[ -z "$SERVER" ]]; then
        read -r -p "PATCH COMMAND HTTPS address: " SERVER
    fi
    if [[ -z "$CA_SOURCE" ]]; then
        read -r -p "Trusted CA PEM file (blank to generate test-only CA): " CA_SOURCE
    fi
fi

if [[ "$MODE" == "install" ]]; then
    if (( EUID != 0 )); then
        echo "ERROR: Installation requires root privileges." >&2
        exit 1
    fi

    echo "Installation mode requested."
    echo "Production installation is not enabled yet."
    echo "Use --test-install to validate an isolated installation."
    exit 1
fi

if [[ "$MODE" == "test-install" ]]; then
    SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
    PACKAGE="${SCRIPT_DIR}/dist/arby-patch-agent.tar.gz"
    INSTALLER="${SCRIPT_DIR}/install-files.py"

    TEST_ROOT="$(mktemp -d)"
    trap 'rm -rf -- "$TEST_ROOT"' EXIT

    echo "=== ISOLATED AGENT INSTALLATION ==="

    python3 "$INSTALLER" "$PACKAGE" --root "$TEST_ROOT"

    echo
    echo "=== INSTALLED RELEASE ==="

    test -L "$TEST_ROOT/opt/arby-patch-agent/agent"
    test -d "$TEST_ROOT/opt/arby-patch-agent/agent"
    test "$(stat -c %a "$TEST_ROOT/var/lib/arby-patch-agent")" = "700"

    echo "[OK] Agent release activated"
    echo "[OK] Private state directory verified"

    echo
    echo "=== TRUSTED HTTPS CA INSTALLATION ==="

    CA_INSTALLER="${SCRIPT_DIR}/install-ca.py"
    if [[ -z "$SERVER" ]]; then
        SERVER="https://patch-command.example.test"
    fi
    if [[ -z "$CA_SOURCE" ]]; then
        CERT_HOST="$(python3 -c 'import sys, urllib.parse; print(urllib.parse.urlsplit(sys.argv[1]).hostname or "")' "$SERVER")"
        [[ -n "$CERT_HOST" ]] || { echo "Invalid server URL" >&2; exit 2; }
        python3 "${SCRIPT_DIR}/generate-certificates.py" \
          --hostname "$CERT_HOST" --output "$TEST_ROOT/generated-certs"
        CA_SOURCE="$TEST_ROOT/generated-certs/ca.crt"
    fi

    python3 "$CA_INSTALLER" "$CA_SOURCE" --root "$TEST_ROOT"

    test -f "$TEST_ROOT/etc/arby-patch-agent/ca.crt"
    test ! -L "$TEST_ROOT/etc/arby-patch-agent/ca.crt"

    echo "[OK] Trusted CA installed into isolated root"

    echo
    echo "=== PORTABLE AGENT CONFIGURATION ==="
    python3 "${SCRIPT_DIR}/setup-config.py" --root "$TEST_ROOT" --server "$SERVER"
    test -f "$TEST_ROOT/etc/arby-patch-agent/config.json"
    echo "[OK] Agent configuration installed"

    echo
    echo "=== SYSTEMD UNIT INSTALLATION ==="

    SYSTEMD_INSTALLER="${SCRIPT_DIR}/install-systemd.py"

    python3 "$SYSTEMD_INSTALLER" --root "$TEST_ROOT"

    for unit in arby-patch-agent.service arby-patch-agent.timer; do
        UNIT_PATH="${TEST_ROOT}/etc/systemd/system/${unit}"

        test -f "$UNIT_PATH"
        test ! -L "$UNIT_PATH"
        test "$(stat -c %a "$UNIT_PATH")" = "644"

        echo "[OK] Verified $unit"
    done

    echo
    echo "=== INSTALLED AGENT SMOKE TEST ==="

    (
        cd "$TEST_ROOT/opt/arby-patch-agent"
        python3 -m agent scan
    )

    echo "[OK] Installed agent executed successfully"
    echo "[OK] Test root will be removed automatically"
    exit 0
fi

AGENT_DIR="/opt/arby-patch-agent"
STATE_DIR="/var/lib/arby-patch-agent"
CONFIG_DIR="/etc/arby-patch-agent"
SERVER="${SERVER:-<not-configured>}"

if [[ ! -r /etc/os-release ]]; then
    echo "ERROR: Cannot identify operating system." >&2
    exit 1
fi

# shellcheck disable=SC1091
source /etc/os-release

case "${ID:-}" in
    arch)
        PLATFORM="arch"
        DEPENDENCIES="python pacman-contrib python-cryptography"
        ;;
    debian)
        PLATFORM="debian"
        DEPENDENCIES="python3 apt python3-cryptography"
        ;;
    *)
        echo "ERROR: Unsupported distribution: ${ID:-unknown}" >&2
        exit 1
        ;;
esac

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE="${SCRIPT_DIR}/dist/arby-patch-agent.tar.gz"

echo "=== INSTALLER PREFLIGHT ==="

if [[ ! -f "$PACKAGE" ]]; then
    echo "[ERROR] Agent package missing: $PACKAGE" >&2
    exit 1
fi

VALIDATOR="${SCRIPT_DIR}/validate-package.py"

if [[ ! -f "$VALIDATOR" ]]; then
    echo "[ERROR] Package validator missing: $VALIDATOR" >&2
    exit 1
fi

if ! python3 "$VALIDATOR" "$PACKAGE"; then
    echo "[ERROR] Agent package failed security validation." >&2
    exit 1
fi

echo "[OK] Agent package security validation passed"
echo

echo "=== DEPENDENCY CHECK ==="

missing=0

if command -v python3 >/dev/null 2>&1; then
    echo "[OK] Python 3"
else
    echo "[MISSING] Python 3"
    missing=1
fi

if python3 -c 'import cryptography; from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey' >/dev/null 2>&1; then
    echo "[OK] Python cryptography with Ed25519 support"
else
    echo "[MISSING] Python cryptography with Ed25519 support"
    missing=1
fi

if command -v systemctl >/dev/null 2>&1; then
    echo "[OK] systemctl"
else
    echo "[MISSING] systemctl"
    missing=1
fi

if [[ "$PLATFORM" == "arch" ]]; then
    if command -v checkupdates >/dev/null 2>&1; then
        echo "[OK] checkupdates"
    else
        echo "[MISSING] checkupdates (pacman-contrib)"
        missing=1
    fi
else
    if command -v apt >/dev/null 2>&1; then
        echo "[OK] apt"
    else
        echo "[MISSING] apt"
        missing=1
    fi
fi

echo

if (( missing )); then
    echo "WARNING: Dependencies must be installed before deployment."
    echo
fi

cat <<EOF
========================================
 ARBY PATCH AGENT — INSTALLER DRY RUN
========================================

Detected OS:       ${PRETTY_NAME:-unknown}
Platform:          ${PLATFORM}
Dependencies:      ${DEPENDENCIES}

Application:       ${AGENT_DIR}
Persistent state:  ${STATE_DIR}
Configuration:     ${CONFIG_DIR}
PATCH COMMAND:     ${SERVER}

Planned installation:
  1. Verify required dependencies
  2. Install standalone agent Python modules
  3. Create private persistent state directory
  4. Install and verify trusted HTTPS CA
  5. Install systemd service and timer
  6. Leave automatic scheduling disabled
  7. Leave enrollment pending manual approval

Safety:
  - No unattended package upgrades
  - No automatic reboots
  - No credentials copied from another machine
  - No automatic agent registration

DRY RUN ONLY — No changes made.
========================================
EOF
