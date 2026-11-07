#!/usr/bin/env bash
# Versionary controlled-beta guided agent setup. Fresh disposable VM only.
set -Eeuo pipefail
umask 077
TAG=v0.1.0-beta.2
BASE=https://github.com/broncbash/Versionary/releases/download/$TAG
PIN=3b42b8dfaddf58fa004e1e626314599bf10aa2f8b9c3932b046ded92ecc2fb3b
SERVER='' CA='' CA_FINGERPRINT='' INSTALL_DEPS=false TIMER=false
usage() { cat <<'HELP'
Usage: bash install-versionary-agent.sh [--server https://IP:8766] [--ca-cert /path/to/ca.crt] [--ca-fingerprint SHA256_HEX] [--install-deps] [--enable-timer]
CA certificate must be securely obtained from your Versionary server and
its fingerprint independently verified. Never transfer server private keys.
Interactive prompts are used for omitted server URL and CA path.
Administrator must approve agent in dashboard; no unattended patching.
HELP
}
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
 --server) (($#>=2)) || die 'Missing --server value'; SERVER=$2; shift 2;;
 --ca-cert) (($#>=2)) || die 'Missing --ca-cert value'; CA=$2; shift 2;;
 --ca-fingerprint) (($#>=2)) || die 'Missing --ca-fingerprint value'; CA_FINGERPRINT=$2; shift 2;;
 --install-deps) INSTALL_DEPS=true; shift;;
 --enable-timer) TIMER=true; shift;;
 --help|-h) usage; exit 0;;
 *) die "Unknown option $1";;
 esac
done
cat <<'EXPLAIN'
Agent setup:
  This agent will request enrollment. Approve it in the server dashboard.
  Observer reporting scans for available package updates and sends the
  results to the server; it never installs updates or reboots your machine.
  Optional daily timer: repeats observer-only reporting once per day.
  The CA certificate is public, but must be verified before trusting it.\n  Discovery results are UNTRUSTED hints until the CA is verified.
EXPLAIN
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
if [[ -z $SERVER && -t 0 ]]; then
 echo 'Searching the local /24 network for Versionary beta servers (discovery only; not trusted)...'
 if command -v python3 >/dev/null 2>&1 && command -v ip >/dev/null 2>&1; then
  mapfile -t FOUND < <(python3 - <<'PY'
import concurrent.futures,ipaddress,json,ssl,subprocess,urllib.request
hosts=set()
try:
 for line in subprocess.check_output(['ip','-o','-4','addr','show','scope','global'],text=True,timeout=3).splitlines():
  for word in line.split():
   try: iface=ipaddress.ip_interface(word)
   except ValueError: continue
   if iface.ip.is_private and not iface.ip.is_loopback:
    hosts.update(str(ip) for ip in ipaddress.ip_network(str(iface.ip)+'/24',strict=False).hosts())
except (OSError,subprocess.SubprocessError): pass
def probe(ip):
 try:
  with urllib.request.urlopen('https://'+ip+':8766/health',timeout=0.6,context=ssl._create_unverified_context()) as response:
   payload=json.loads(response.read(2048))
   if payload.get('status')=='online' and payload.get('mode')=='isolated-https-beta':
    return 'https://'+ip+':8766'
 except Exception: pass
with concurrent.futures.ThreadPoolExecutor(max_workers=32) as pool:
 for url in filter(None,pool.map(probe,sorted(hosts)[:512])): print(url)
PY
  )
  if (( ${#FOUND[@]} )); then
   printf 'Discovered candidate(s):\n'
   for i in "${!FOUND[@]}"; do printf '  %d) %s\n' "$((i+1))" "${FOUND[i]}"; done
   read -r -p 'Select number (Enter for manual URL): ' choice
   if [[ $choice =~ ^[0-9]+$ ]] && ((choice>=1 && choice<=${#FOUND[@]})); then SERVER=${FOUND[choice-1]}; fi
  else echo 'No Versionary server discovered; manual address required.'; fi
 fi
fi
[[ -n $SERVER ]] || { [[ -t 0 ]] && read -r -p 'Versionary HTTPS server URL: ' SERVER || die 'Missing --server'; }
# Users often paste the dashboard address instead of the API base URL.
if [[ $SERVER == */admin/dashboard ]]; then
 SERVER=${SERVER%/admin/dashboard}
 printf 'Using server base URL: %s\n' "$SERVER"
fi
[[ $SERVER == https://* ]] || die 'HTTPS server URL required'
if [[ -z $CA ]]; then
 echo 'Automatic CA download requires the SHA256 certificate fingerprint from the SERVER console.'
 echo 'On the server run: sudo openssl x509 -in /var/lib/versionary/certs/ca.crt -noout -fingerprint -sha256'
 [[ -n $CA_FINGERPRINT ]] || { [[ -t 0 ]] && read -r -p 'Server CA SHA256 fingerprint (hex): ' CA_FINGERPRINT || die 'Missing --ca-fingerprint'; }
 [[ $CA_FINGERPRINT =~ ^([[:xdigit:]]{2}:){31}[[:xdigit:]]{2}$ || $CA_FINGERPRINT =~ ^[[:xdigit:]]{64}$ ]] || die 'Invalid SHA256 fingerprint'
 command -v curl >/dev/null 2>&1 || die 'curl required for CA download; install curl first'
 command -v openssl >/dev/null 2>&1 || die 'openssl required to verify CA; install openssl first'
 CA_FINGERPRINT=${CA_FINGERPRINT//:/}
 CA_FINGERPRINT=${CA_FINGERPRINT,,}
 CA="$HOME/versionary-server-ca.crt"
 [[ ! -e $CA && ! -L $CA ]] || die "CA destination exists: $CA; use --ca-cert to reuse a verified certificate"
 echo 'Retrieving PUBLIC CA from selected server; TLS identity not trusted until fingerprint matches...'
 curl --insecure --fail --silent --show-error --max-time 10 "$SERVER/api/v1/bootstrap/ca" -o "$CA.part" || die 'CA download unavailable; use --ca-cert with a verified local copy'
 observed=$(openssl x509 -in "$CA.part" -noout -fingerprint -sha256 | sed 's/^.*=//' | tr -d ':' | tr '[:upper:]' '[:lower:]') || die 'Invalid downloaded CA'
 if [[ $observed != "$CA_FINGERPRINT" ]]; then rm -f "$CA.part"; die 'CA fingerprint MISMATCH. Do not trust this server.'; fi
 mv "$CA.part" "$CA"
 chmod 600 "$CA"
 echo 'CA fingerprint verified against server-console fingerprint.'
fi
[[ -f $CA && ! -L $CA ]] || die "CA file not found on THIS agent machine: $CA"
CA=$(realpath -- "$CA")
command -v curl >/dev/null 2>&1 && curl --fail --silent --show-error --cacert "$CA" --max-time 10 "$SERVER/health" >/dev/null || die 'Verified HTTPS health check failed; check server address and CA'

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
echo 'The next step may offer to install scanner dependencies and enable a daily timer.'
as_root bash source/installer/versionary-agent-guided-install.sh "$@"
