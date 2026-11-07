#!/usr/bin/env bash
# Versionary beta guided server setup. Fresh disposable systemd VM only.
set -Eeuo pipefail
umask 077
TAG=v0.1.0-beta.2
BASE=https://github.com/broncbash/Versionary/releases/download/$TAG
PIN=3b42b8dfaddf58fa004e1e626314599bf10aa2f8b9c3932b046ded92ecc2fb3b
IP='' PORT=8766 FLEET=ask YES=false
usage() { echo 'Usage: bash install-versionary.sh [--address IP] [--port 8766] [--beta-fleet|--no-beta-fleet] [--yes]'; }
die() { echo "ERROR: $*" >&2; exit 1; }

# Run privileged commands without assuming sudo access.
as_root() {
 if (( EUID == 0 )); then
  "$@"
 elif command -v sudo >/dev/null 2>&1 && sudo -v; then
  sudo "$@"
 elif command -v su >/dev/null 2>&1; then
  printf -v root_command '%q ' "$@"
  echo 'Root password may be required.'
  su -c "$root_command"
 else
  die 'Administrator privileges required; run as root or configure sudo.'
 fi
}
ask() { local a; read -r -p "$1 [y/N] " a; [[ $a == y || $a == Y || $a == yes || $a == YES ]]; }
while (($#)); do
 case "$1" in
 --address) IP=$2; shift 2;; --port) PORT=$2; shift 2;;
 --beta-fleet) FLEET=true; shift;; --no-beta-fleet) FLEET=false; shift;;
 --yes) YES=true; shift;; --help|-h) usage; exit 0;;
 *) die "Unknown option $1";;
 esac
done
[[ $PORT =~ ^[0-9]+$ ]] && ((10#$PORT >= 1024 && 10#$PORT <= 65535)) || die 'Invalid HTTPS port'
# On minimal Arch/Debian guests, offer to install missing bootstrap tools.
bootstrap_dependencies() {
 local missing=() cmd pkgmgr='' packages=()
 for cmd in curl sha256sum python3 openssl; do
  command -v "$cmd" >/dev/null 2>&1 || missing+=("$cmd")
 done
 (("${#missing[@]}" == 0)) && return 0
 if command -v pacman >/dev/null 2>&1; then
  pkgmgr=pacman
  for cmd in "${missing[@]}"; do
   case "$cmd" in curl) packages+=(curl);; sha256sum) packages+=(coreutils);; python3) packages+=(python);; openssl) packages+=(openssl);; esac
  done
 elif command -v apt-get >/dev/null 2>&1; then
  pkgmgr=apt
  for cmd in "${missing[@]}"; do
   case "$cmd" in curl) packages+=(curl);; sha256sum) packages+=(coreutils);; python3) packages+=(python3);; openssl) packages+=(openssl);; esac
  done
 else die "Missing ${missing[*]}; install these prerequisites with your system package manager"; fi
 printf 'Missing required tools: %s\n' "${missing[*]}"
 [[ -t 0 ]] && ask 'Install missing prerequisites using the OS package manager?' || die 'Missing prerequisites in noninteractive mode'
 if [[ $pkgmgr == pacman ]]; then
  echo 'Arch package installation may perform a system upgrade.'
  as_root pacman -Syu --needed -- "${packages[@]}"
 else
  as_root apt-get update
  as_root env DEBIAN_FRONTEND=noninteractive apt-get install -y -- "${packages[@]}"
 fi
 for cmd in "${missing[@]}"; do command -v "$cmd" >/dev/null 2>&1 || die "Still missing $cmd"; done
}
bootstrap_dependencies
for cmd in systemctl ip; do command -v "$cmd" >/dev/null || die "Missing $cmd"; done
[[ -d /run/systemd/system ]] || die 'Requires systemd'
[[ ! -e /opt/versionary && ! -e /var/lib/versionary && ! -e /etc/systemd/system/versionary-server.service ]] || die 'Existing or partial installation detected; refusing overwrite'
if [[ -z $IP ]]; then
 mapfile -t IPS < <(ip -o -4 addr show scope global | awk '{print $4}' | cut -d/ -f1)
 if (( ${#IPS[@]} == 1 )); then IP=${IPS[0]}
 elif [[ -t 0 ]]; then printf 'Detected IPs: %s\n' "${IPS[*]}"; read -r -p 'Server IP: ' IP
 else die 'Specify --address IP'; fi
fi
python3 - "$IP" <<'PY'
import ipaddress,sys
try:
 a=ipaddress.ip_address(sys.argv[1])
 assert not (a.is_loopback or a.is_unspecified or a.is_multicast)
except (ValueError,AssertionError): raise SystemExit('Invalid server IP')
PY
if [[ $FLEET == ask ]]; then
 cat <<'EXPLAIN'
Beta fleet options:
  Enrollment ON: other machines can request to join this server.
  You must explicitly approve each agent in the dashboard.
  Reporting ON: approved agents can send heartbeats and lists of available
  package updates. Reporting does NOT install updates, reboot hosts, or
  grant remote shell access.
  OFF: the server runs but cannot accept beta agent enrollment/reports.
EXPLAIN
 if [[ $YES == true ]]; then FLEET=false
 elif ask 'Enable beta agent enrollment and observer-only reporting?'; then FLEET=true
 else FLEET=false; fi
fi
printf 'Server: https://%s:%s\nBeta enrollment/reporting: %s\n' "$IP" "$PORT" "$FLEET"
[[ $YES == true ]] || { [[ -t 0 ]] && ask 'Install on this fresh disposable VM?' || die 'Cancelled'; }
DIR="$HOME/.cache/versionary-installer/$TAG"
mkdir -p "$DIR"
cd "$DIR"
echo 'Downloading and verifying official release...'
for file in "versionary-$TAG.tar.gz" "versionary-$TAG-manifest.json" "versionary-$TAG-agent.tar.gz" SHA256SUMS; do
 if [[ ! -f $file ]]; then
  curl -fL --retry 2 --show-error -o "$file.part" "$BASE/$file" || die "Download failed: $file"
  mv "$file.part" "$file"
 fi
done
printf '%s  %s\n' "$PIN" "versionary-$TAG.tar.gz" | sha256sum -c - || die 'Pinned release mismatch'
sha256sum -c SHA256SUMS || die 'Release checksum mismatch'
mkdir -p source
python3 - "versionary-$TAG.tar.gz" "versionary-$TAG-manifest.json" <<'PY'
import hashlib,json,pathlib,sys,tarfile
a,m=map(pathlib.Path,sys.argv[1:])
meta=json.loads(m.read_text())
assert hashlib.sha256(a.read_bytes()).hexdigest()==meta['sha256']
files=meta['files']
with tarfile.open(a,'r:gz') as tf:
 members=tf.getmembers()
 names=[x.name for x in members]
 assert len(names)==len(set(names))==len(files)
 for item in members:
  path=pathlib.PurePosixPath(item.name)
  assert item.isfile() and not path.is_absolute() and '..' not in path.parts and item.name in files
  data=tf.extractfile(item).read()
  assert len(data)==files[item.name]['size']
  assert hashlib.sha256(data).hexdigest()==files[item.name]['sha256']
  target=pathlib.Path('source')/item.name
  target.parent.mkdir(parents=True,exist_ok=True)
  target.write_bytes(data)
PY
installer=(python3 source/installer/versionary-server-install.py --archive "$DIR/versionary-$TAG.tar.gz" --manifest "$DIR/versionary-$TAG-manifest.json" --tls-identity "$IP" --bind-address "$IP" --port "$PORT")
echo 'Checking installation...'
"${installer[@]}" --mode dry-run
echo 'Installing server...'
as_root bash -c 'umask 022; exec "$@"' bash "${installer[@]}" --mode install --confirm-disposable
if [[ $FLEET == true ]]; then
 as_root install -d -m 755 /etc/systemd/system/versionary-server.service.d
 printf '%s\n' '[Service]' 'Environment=VERSIONARY_BETA_ENROLLMENT=true' 'Environment=VERSIONARY_BETA_REPORTING=true' 'Environment=VERSIONARY_DISTRIBUTION_ENABLED=false' | as_root tee /etc/systemd/system/versionary-server.service.d/beta-fleet.conf >/dev/null
 as_root systemctl daemon-reload
 as_root systemctl restart versionary-server.service
fi
as_root systemctl is-active --quiet versionary-server.service || die 'Service failed; check journalctl -u versionary-server.service'
printf '\nINSTALL=PASS\nDashboard: https://%s:%s/admin/dashboard\n' "$IP" "$PORT"
echo 'CA: /var/lib/versionary/certs/ca.crt'
echo 'For secure agent auto-download, copy this fingerprint from the SERVER console:'
as_root openssl x509 -in /var/lib/versionary/certs/ca.crt -noout -fingerprint -sha256 || true
echo 'Admin token: sudo cat /var/lib/versionary/admin-token (keep private)'
echo 'PRODUCTION_APPROVED=NO'
