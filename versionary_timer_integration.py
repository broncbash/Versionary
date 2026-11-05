"""Build and validate INERT user systemd units; never install/activate them."""
import argparse
import os
import shlex
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PREVIEW = ROOT / '.versionary-timer-integration-preview'
SERVICE = 'versionary-beta-scan.service'
TIMER = 'versionary-beta-scan.timer'


def safe_path(path):
    value = str(path)
    if any(c in value for c in '\n\r\x00'):
        raise ValueError('Unsafe path characters')
    return value


def units(root=ROOT):
    root = Path(root).resolve()
    python = root / '.venv/bin/python'
    runner = root / 'versionary_background.py'
    for path in (root, python, runner):
        safe_path(path)
    # Validate systemd path syntax before checking filesystem existence.
    # Invalid paths must be rejected regardless of whether files exist.
    for path in (root, python, runner):
        if any(c in str(path) for c in ('"', '\\', '%')):
            raise ValueError('Unsupported character in unit path')
    if not python.is_file() or not runner.is_file():
        raise ValueError('Missing virtualenv Python or background runner')
    service = (
        '[Unit]\nDescription=Versionary local beta read-only background scan (PREVIEW)\n'
        '[Service]\nType=oneshot\n'
        f'WorkingDirectory="{root}"\n'
        f'ExecStart="{python}" "{runner}"\n'
        'NoNewPrivileges=yes\nPrivateTmp=yes\n'
        'UMask=0077\nTimeoutStartSec=300\n'
        'StandardOutput=null\nStandardError=journal\n'
    )
    timer = (
        '[Unit]\nDescription=Versionary beta six-hour scan timer (PREVIEW)\n'
        '[Timer]\nOnStartupSec=10min\nOnUnitInactiveSec=6h\n'
        'AccuracySec=5min\nRandomizedDelaySec=2min\n'
        'Persistent=false\n'
        f'Unit={SERVICE}\n'
        '[Install]\nWantedBy=timers.target\n'
    )
    return {SERVICE: service, TIMER: timer}


def write_preview(root=ROOT, output=None):
    root = Path(root).resolve()
    output = Path(output) if output is not None else root / '.versionary-timer-integration-preview'
    if output.is_symlink():
        raise ValueError('Refusing symlink preview directory')
    output.mkdir(mode=0o700, exist_ok=True)
    if output.stat().st_uid != os.getuid():
        raise ValueError('Preview directory must be owned by current user')
    os.chmod(output, 0o700)
    generated = units(root)
    # Never overwrite any existing preview files, including symlinks.
    if any((output / name).exists() or (output / name).is_symlink() for name in generated):
        raise ValueError('Preview already exists; refusing overwrite')
    for name, content in generated.items():
        path = output / name
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'w') as f:
            f.write(content)
    return output


def verify_preview(output, executable='systemd-analyze'):
    service = Path(output) / SERVICE
    timer = Path(output) / TIMER
    try:
        proc = subprocess.run([executable, 'verify', str(service), str(timer)],
                              capture_output=True, text=True, timeout=30, check=False)
    except FileNotFoundError:
        return 'unavailable', 'systemd-analyze not installed; syntax verification not performed'
    except subprocess.TimeoutExpired:
        return 'failed', 'systemd-analyze verify timed out'
    if proc.returncode:
        # Unit validation output contains only local paths, never tokens.
        return 'failed', (proc.stderr or proc.stdout).strip()[:3000]
    return 'passed', 'systemd-analyze verify passed'


def main():
    parser = argparse.ArgumentParser(description='Generate inactive Versionary timer preview')
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    if args.verify_only:
        if not (PREVIEW / SERVICE).is_file() or not (PREVIEW / TIMER).is_file():
            parser.error('Preview missing; generate it first')
        output = PREVIEW
    else:
        output = write_preview()
        print('Created INACTIVE user-unit preview:', output)
    status, detail = verify_preview(output)
    print('Unit verification:', status, '-', detail)
    print('NO systemd units installed, enabled, started, or activated.')
    return 1 if status == 'failed' else 0


if __name__ == '__main__':
    raise SystemExit(main())
