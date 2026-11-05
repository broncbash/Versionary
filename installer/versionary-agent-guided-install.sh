#!/usr/bin/env bash
# Versionary disposable-VM guided agent installer. Not production approved.
set -Eeuo pipefail
umask 077

usage() {
  cat <<'HELP'
Usage:
  sudo bash installer/versionary-agent-guided-install.sh \
    --distribution /path/to/versionary-agent-distribution.tar.gz \
    --ca-cert /path/to/ca.crt \
    --server https://HOST:8766 [--install-deps] [--enable-timer]

Or omit arguments for interactive prompts. Requires a verified release tree
with installer/versionary-beta-agent-bootstrap.sh and its dependencies.
The installer waits up to 10 minutes for dashboard approval. It never
installs package updates or enables the reporting timer without opt-in.
HELP
}
fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
[[ ${EUID} -eq 0 ]] || fail 'Run as root with sudo.'
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
BOOTSTRAP="$HERE/versionary-beta-agent-bootstrap.sh"
CLI=/opt/versionary-agent/versionary_agent_cli.py
DIST='' CA='' SERVER='' INSTALL_DEPS=false ENABLE_TIMER=false
while (($#)); do
  case "$1" in
    --distribution|--ca-cert|--server)
      (($# >= 2)) || fail "Missing value for $1"
      case "$1" in
        --distribution) DIST=$2;;
        --ca-cert) CA=$2;;
        --server) SERVER=$2;;
      esac
      shift 2;;
    --install-deps) INSTALL_DEPS=true; shift;;
    --enable-timer) ENABLE_TIMER=true; shift;;
    --help|-h) usage; exit 0;;
    *) fail "Unknown option: $1";;
  esac
done

if [[ -t 0 ]]; then
  if [[ -z $DIST ]]; then read -r -p 'Verified agent distribution archive: ' DIST; fi
  if [[ -z $CA ]]; then read -r -p 'Server CA certificate file: ' CA; fi
  if [[ -z $SERVER ]]; then read -r -p 'Server HTTPS URL: ' SERVER; fi
  if [[ $INSTALL_DEPS == false ]]; then
    read -r -p 'Allow installation of missing system dependencies? [y/N] ' answer
    [[ ${answer,,} == y || ${answer,,} == yes ]] && INSTALL_DEPS=true
  fi
  if [[ $ENABLE_TIMER == false ]]; then
    read -r -p 'Enable daily observer-only reporting after enrollment? [y/N] ' answer
    [[ ${answer,,} == y || ${answer,,} == yes ]] && ENABLE_TIMER=true
  fi
fi

[[ -n $DIST && -n $CA && -n $SERVER ]] || { usage; fail 'Missing required input.'; }
[[ -f $BOOTSTRAP ]] || fail 'Bootstrap missing. Run from the verified Versionary release tree.'
[[ -f $DIST && ! -L $DIST ]] || fail 'Distribution archive missing or symlinked.'
[[ -f $CA && ! -L $CA ]] || fail 'CA certificate missing or symlinked.'
[[ $SERVER == https://* ]] || fail 'HTTPS server URL required.'

if [[ -e $CLI ]]; then
  echo 'Existing Versionary installation detected.'
  echo 'Preserving existing configuration, credentials and identity.'
  [[ -f /etc/versionary-agent/config.json ]] || fail 'Incomplete existing installation; manual recovery required.'
  python3 - "$SERVER" <<'PY'
import json, sys
from pathlib import Path
config = json.loads(Path('/etc/versionary-agent/config.json').read_text())
if config.get('server') != sys.argv[1]:
    raise SystemExit('ERROR: Existing server differs; refusing reconfiguration.')
PY
  python3 "$CLI" --system status
else
  [[ ! -e /opt/versionary-agent && ! -e /etc/versionary-agent && ! -e /var/lib/versionary-agent ]] || fail 'Partial installation found. Preserve state and repair manually before retry.'
  args=(install --distribution "$DIST" --ca-cert "$CA" --server "$SERVER")
  [[ $INSTALL_DEPS == true ]] && args+=(--install-deps)
  bash "$BOOTSTRAP" "${args[@]}"
fi

# If credentials already exist, do not re-register or re-enroll.
if [[ -f /var/lib/versionary-agent/credential.json ]]; then
  echo 'Existing enrollment credential detected; retaining it.'
else
  if [[ ! -f /var/lib/versionary-agent/identity.json ]]; then
    echo 'No identity found; requesting registration.'
    python3 "$CLI" --system register
  fi
  echo
  echo 'Approve this agent in the Versionary dashboard.'
  echo "Dashboard: ${SERVER%/}/admin/dashboard"
  echo 'Waiting up to 10 minutes for approval...'
  approved=false
  for ((attempt=1; attempt<=40; attempt++)); do
    # Enrollment may be retried while approval is pending. The agent CLI
    # retains its private enrollment key and handles server rejection.
    if output=$(python3 "$CLI" --system enroll 2>&1); then
      printf '%s\n' "$output"
      approved=true
      break
    fi
    if ((attempt < 40)); then
      printf '[WAITING] Administrator approval pending (%d/40)...\n' "$attempt"
      sleep 15
    else
      printf '[ERROR] Enrollment did not complete: %s\n' "$output" >&2
    fi
  done
  [[ $approved == true ]] || fail 'Enrollment not completed within 10 minutes. Approval may still be pending; rerun this installer after approving.'
fi

python3 "$CLI" --system heartbeat
if python3 "$CLI" --system report; then
  echo 'Initial update report delivered.'
else
  echo 'WARNING: Initial update report failed; check scanner dependencies and retry.' >&2
fi

if [[ $ENABLE_TIMER == true ]]; then
  systemctl daemon-reload
  systemctl enable --now versionary-agent.timer
  echo 'Daily observer-only reporting timer enabled.'
else
  echo 'Reporting timer unchanged (not enabled by this command).'
fi

echo 'VERSIONARY_GUIDED_AGENT_INSTALL=COMPLETE'
echo 'No system package updates were installed by Versionary.'
