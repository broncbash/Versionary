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
ask() { local a; read -r -p "$1 [y/N] " a; [[ $a == y || $a == Y || $a == yes || $a == YES ]]; }
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
cat <<'EXPLAIN'
Agent setup:
  This agent will request enrollment. Approve it in the server dashboard.
  Observer reporting scans for available package updates and sends the
  results to the server; it never installs updates or reboots your machine.
  Optional daily timer: repeats observer-only reporting once per day.
  The CA certificate is public, but must be verified before trusting it.\n  Discovery results are UNTRUSTED hints until the CA is verified.
EXPLAIN
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
[[ -n $CA ]] || { [[ -t 0 ]] && read -r -p 'Verified server CA certificate path: ' CA || die 'Missing --ca-cert'; }
[[ $SERVER == https://* ]] || die 'HTTPS server URL required'
[[ -f $CA && ! -L $CA ]] || die "CA file not found on THIS agent machine: $CA. The server's /var/lib/versionary/certs/ca.crt is not accessible locally. Copy the public CA to the agent and independently verify its SHA256 fingerprint."
CA=$(realpath -- "$CA")
# On minimal Arch/Debian guests, offer to install missing bootstrap tools.
bootstrap_dependencies() {
 local missing=() cmd pkgmgr='' packages=()
 for cmd in curl sha256sum python3 sudo; do
  command -v "$cmd" >/dev/null 2>&1 || missing+=("$cmd")
 done
 (("${#missing[@]}" == 0)) && return 0
 if command -v pacman >/dev/null 2>&1; then
  pkgmgr=pacman
  for cmd in "${missing[@]}"; do
   case "$cmd" in curl) packages+=(curl);; sha256sum) packages+=(coreutils);; python3) packages+=(python);; sudo) packages+=(sudo);; esac
  done
 elif command -v apt-get >/dev/null 2>&1; then
  pkgmgr=apt
  for cmd in "${missing[@]}"; do
   case "$cmd" in curl) packages+=(curl);; sha256sum) packages+=(coreutils);; python3) packages+=(python3);; sudo) packages+=(sudo);; esac
  done
 else die "Missing ${missing[*]}; install these prerequisites with your system package manager"; fi
 printf 'Missing required tools: %s\n' "${missing[*]}"
 [[ -t 0 ]] && ask 'Install missing prerequisites using the OS package manager?' || die 'Missing prerequisites in noninteractive mode'
 if (( EUID == 0 )); then
  if [[ $pkgmgr == pacman ]]; then pacman -Syu --needed -- "${packages[@]}"; else apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y -- "${packages[@]}"; fi
 elif command -v sudo >/dev/null 2>&1; then
  if [[ $pkgmgr == pacman ]]; then sudo pacman -Syu --needed -- "${packages[@]}"; else sudo apt-get update && sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y -- "${packages[@]}"; fi
 else
  command -v su >/dev/null 2>&1 || die 'No sudo or su available. Install prerequisites as root.'
  echo 'Root password required to install missing prerequisites.'
  if [[ $pkgmgr == pacman ]]; then su -c "pacman -Syu --needed -- ${packages[*]}" || die 'Root package installation failed'
  else su -c "apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y -- ${packages[*]}" || die 'Root package installation failed'; fi
  # sudo may be installed but user might not be in sudoers.
  echo 'If sudo reports that your account is not authorized, add it to sudoers using your distribution setup.'
 fi
 for cmd in "${missing[@]}"; do command -v "$cmd" >/dev/null 2>&1 || die "Still missing $cmd"; done
}
bootstrap_dependencies
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
sudo bash source/installer/versionary-agent-guided-install.sh "$@"
