#!/usr/bin/env bash
# Versionary controlled-beta guided agent setup. Fresh disposable VM only.
set -Eeuo pipefail
umask 077
TAG=v0.1.0-beta.1
BASE=https://github.com/broncbash/Versionary/releases/download/$TAG
PIN=4309194d3d993a0a7d1c238d0ac514963b53c80afd5263c304f36a11dc26542a
SERVER='' CA='' INSTALL_DEPS=false TIMER=false
usage() { cat <<'HELP'
Usage: bash install-versionary-agent.sh [--server https://IP:8766] [--ca-cert /path/to/ca.crt] [--install-deps] [--enable-timer]
CA certificate must be securely obtained from your Versionary server and
its fingerprint independently verified. Never transfer server private keys.
Interactive prompts are used for omitted server URL and CA path.
Administrator must approve agent in dashboard; no unattended patching.
HELP
}
die() { echo "ERROR: $*" >&2; exit 1; }
while (($#)); do
 case "$1" in
 --server) (($#>=2)) || die 'Missing --server value'; SERVER=$2; shift 2;;
 --ca-cert) (($#>=2)) || die 'Missing --ca-cert value'; CA=$2; shift 2;;
 --install-deps) INSTALL_DEPS=true; shift;;
 --enable-timer) TIMER=true; shift;;
 --help|-h) usage; exit 0;;
 *) die "Unknown option $1";;
 esac
done
[[ -n $SERVER ]] || { [[ -t 0 ]] && read -r -p 'Versionary HTTPS server URL: ' SERVER || die 'Missing --server'; }
[[ -n $CA ]] || { [[ -t 0 ]] && read -r -p 'Verified server CA certificate path: ' CA || die 'Missing --ca-cert'; }
[[ $SERVER == https://* ]] || die 'HTTPS server URL required'
[[ -f $CA && ! -L $CA ]] || die 'CA file missing or symlinked'
CA=$(realpath -- "$CA")
for cmd in curl sha256sum python3 sudo; do command -v "$cmd" >/dev/null || die "Missing $cmd"; done
[[ -d /run/systemd/system ]] || die 'Requires systemd'
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
sha256sum -c SHA256SUMS || die 'Asset checksum mismatch'
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
printf 'Server: %s\nCA: %s\n' "$SERVER" "$CA"
echo 'The guided installer will wait for your dashboard approval.'
set -- --distribution "$DIR/versionary-$TAG-agent.tar.gz" --ca-cert "$CA" --server "$SERVER"
[[ $INSTALL_DEPS == true ]] && set -- "$@" --install-deps
[[ $TIMER == true ]] && set -- "$@" --enable-timer
sudo bash source/installer/versionary-agent-guided-install.sh "$@"
