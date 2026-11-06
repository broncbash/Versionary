#!/usr/bin/env bash
# Versionary beta guided server setup. Fresh disposable systemd VM only.
set -Eeuo pipefail
umask 077
TAG=v0.1.0-beta.1
BASE=https://github.com/broncbash/Versionary/releases/download/$TAG
PIN=4309194d3d993a0a7d1c238d0ac514963b53c80afd5263c304f36a11dc26542a
IP='' PORT=8766 FLEET=ask YES=false
usage() { echo 'Usage: bash install-versionary.sh [--address IP] [--port 8766] [--beta-fleet|--no-beta-fleet] [--yes]'; }
die() { echo "ERROR: $*" >&2; exit 1; }
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
for cmd in curl sha256sum python3 sudo systemctl ip; do command -v "$cmd" >/dev/null || die "Missing $cmd"; done
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
sudo "${installer[@]}" --mode install --confirm-disposable
if [[ $FLEET == true ]]; then
 sudo install -d -m 755 /etc/systemd/system/versionary-server.service.d
 printf '%s\n' '[Service]' 'Environment=VERSIONARY_BETA_ENROLLMENT=true' 'Environment=VERSIONARY_BETA_REPORTING=true' 'Environment=VERSIONARY_DISTRIBUTION_ENABLED=false' | sudo tee /etc/systemd/system/versionary-server.service.d/beta-fleet.conf >/dev/null
 sudo systemctl daemon-reload
 sudo systemctl restart versionary-server.service
fi
sudo systemctl is-active --quiet versionary-server.service || die 'Service failed; check journalctl -u versionary-server.service'
printf '\nINSTALL=PASS\nDashboard: https://%s:%s/admin/dashboard\n' "$IP" "$PORT"
echo 'CA: /var/lib/versionary/certs/ca.crt'
echo 'Admin token: sudo cat /var/lib/versionary/admin-token (keep private)'
echo 'PRODUCTION_APPROVED=NO'
