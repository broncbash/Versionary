#!/usr/bin/env bash
# Disposable-VM beta bootstrap. Not approved for production use.
set -Eeuo pipefail
umask 077

usage() {
  cat <<'HELP'
Usage:
  sudo bash installer/versionary-beta-agent-bootstrap.sh install --distribution FILE --ca-cert FILE --server HTTPS_URL [--install-deps]
  sudo bash installer/versionary-beta-agent-bootstrap.sh complete

Run from a verified Versionary release directory. "install" performs a
verified offline installation into a private staging root, deploys to /,
then registers the agent as pending. Approve in the dashboard, then run
"complete" to enroll, send a heartbeat and report. No timer is enabled.
HELP
}

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
[[ $EUID -eq 0 ]] || fail 'Run with sudo/root.'
[[ $# -gt 0 ]] || { usage; exit 2; }
ACTION=$1; shift
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
RELEASE_DIR=$(cd -- "$SCRIPT_DIR/.." && pwd -P)
CLI=/opt/versionary-agent/versionary_agent_cli.py

if [[ $ACTION == complete ]]; then
  [[ $# -eq 0 ]] || fail 'complete takes no options'
  [[ -f $CLI ]] || fail 'Agent is not installed'
  python3 "$CLI" --system enroll
  python3 "$CLI" --system heartbeat
  python3 "$CLI" --system report
  echo 'AGENT_ENROLLED_AND_REPORTED=PASS'
  exit 0
fi
[[ $ACTION == install ]] || { usage; exit 2; }
DIST= CA= SERVER= DEPS=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --distribution|--ca-cert|--server)
      [[ $# -ge 2 ]] || fail "Missing value for $1"
      case "$1" in
        --distribution) DIST=$2;;
        --ca-cert) CA=$2;;
        --server) SERVER=$2;;
      esac
      shift 2;;
    --install-deps) DEPS=true; shift;;
    *) fail "Unknown option: $1";;
  esac
done
[[ -n $DIST && -n $CA && -n $SERVER ]] || { usage; exit 2; }
[[ -f $DIST && ! -L $DIST ]] || fail 'Distribution missing or symlinked'
[[ -f $CA && ! -L $CA ]] || fail 'CA certificate missing or symlinked'
[[ $SERVER == https://* ]] || fail 'HTTPS server URL required'
[[ -f $RELEASE_DIR/installer/install-agent-offline.py ]] || fail 'Verified release installer missing'
[[ -f $RELEASE_DIR/installer/versionary-agent-system-preflight.py ]] || fail 'Preflight missing'
[[ -f $RELEASE_DIR/installer/systemd/versionary-agent.service ]] || fail 'Systemd templates missing'
[[ -f $RELEASE_DIR/installer/systemd/versionary-agent.timer ]] || fail 'Systemd templates missing'

# Check dependencies appropriate to the host distribution.
. /etc/os-release

NEED_DEPS=false

if ! python3 -c 'import cryptography' >/dev/null 2>&1 ||
   ! command -v curl >/dev/null 2>&1; then
  NEED_DEPS=true
fi

case "${ID:-}" in
  arch|cachyos|endeavouros)
    if ! command -v checkupdates >/dev/null 2>&1; then
      NEED_DEPS=true
    fi
    ;;
esac

if [[ $NEED_DEPS == true ]]; then
  [[ $DEPS == true ]] ||
    fail 'Dependencies missing; rerun with --install-deps to authorize package installation.'

  case "${ID:-}" in
    arch|cachyos|endeavouros)
      pacman -S --needed --noconfirm \
        python python-cryptography curl ca-certificates pacman-contrib
      ;;
    debian|ubuntu)
      apt-get update
      DEBIAN_FRONTEND=noninteractive apt-get install -y \
        python3 python3-cryptography curl ca-certificates
      ;;
    *)
      fail "Unsupported automatic dependency installation for ${ID:-unknown}"
      ;;
  esac
fi

python3 "$RELEASE_DIR/installer/versionary-agent-system-preflight.py" \
  --distribution "$DIST" --ca-cert "$CA" --server "$SERVER"
for path in /opt/versionary-agent /etc/versionary-agent /var/lib/versionary-agent \
  /etc/systemd/system/versionary-agent.service /etc/systemd/system/versionary-agent.timer; do
  [[ ! -e $path && ! -L $path ]] || fail "Existing installation path: $path; refusing overwrite"
done

STAGING=$(mktemp -d /var/tmp/versionary-bootstrap.XXXXXXXX)
chmod 700 "$STAGING"
# Keep staging on failure for investigation; never silently retry over partial deployment.
python3 "$RELEASE_DIR/installer/install-agent-offline.py" \
  --root "$STAGING" --distribution "$DIST" --ca-cert "$CA" --server "$SERVER"
for path in \
  opt/versionary-agent/versionary_agent_cli.py \
  etc/versionary-agent/config.json \
  etc/versionary-agent/ca.crt \
  etc/systemd/system/versionary-agent.service \
  etc/systemd/system/versionary-agent.timer; do
  [[ -f $STAGING/$path ]] || fail "Missing staged file: $path"
done
[[ -L $STAGING/opt/versionary-agent/agent ]] || fail 'Missing staged agent symlink'
[[ -d $STAGING/var/lib/versionary-agent ]] || fail 'Missing staged state directory'

# Initial-install rollback: never remove paths that predated this run.
# This protects against ordinary command failures, not power loss or SIGKILL.
DEPLOYED=()
DEPLOYMENT_COMMITTED=false

rollback_deployment() {
  local result=$?
  trap - EXIT ERR
  if [[ $DEPLOYMENT_COMMITTED != true ]]; then
    echo 'Deployment incomplete; rolling back newly created paths.' >&2
    local index
    for ((index=${#DEPLOYED[@]}-1; index>=0; index--)); do
      rm -rf -- "${DEPLOYED[index]}"
    done
    systemctl daemon-reload || true
    echo "Staging preserved at: $STAGING" >&2
  fi
  exit "$result"
}

trap rollback_deployment EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

deploy_new() {
  local source=$1 destination=$2
  [[ ! -e $destination && ! -L $destination ]] ||
    fail "Destination appeared during installation: $destination"
  # Record the destination before copying so partial copies are removed.
  DEPLOYED+=("$destination")
  cp -a -- "$source" "$destination"
}

install -d -m 755 /opt /etc/systemd/system /var/lib

deploy_new "$STAGING/opt/versionary-agent" /opt/versionary-agent
deploy_new "$STAGING/etc/versionary-agent" /etc/versionary-agent
deploy_new "$STAGING/var/lib/versionary-agent" /var/lib/versionary-agent
deploy_new "$STAGING/etc/systemd/system/versionary-agent.service" \
  /etc/systemd/system/versionary-agent.service
deploy_new "$STAGING/etc/systemd/system/versionary-agent.timer" \
  /etc/systemd/system/versionary-agent.timer

systemctl daemon-reload
DEPLOYMENT_COMMITTED=true
trap - EXIT INT TERM

python3 "$CLI" --system status
python3 "$CLI" --system register
echo 'AGENT_INSTALLED_REGISTERED_PENDING=PASS'
echo 'Approve this agent in the dashboard, then run:'
echo '  sudo bash installer/versionary-beta-agent-bootstrap.sh complete'
echo 'Timer remains disabled. No updates installed.'
