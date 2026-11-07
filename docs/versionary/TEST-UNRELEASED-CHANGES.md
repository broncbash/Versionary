# Testing Versionary development changes before a new beta release

## What you can download now

The GitHub `main` branch is public: https://github.com/broncbash/Versionary . You can clone the source or download the repository ZIP using GitHub's **Code → Download ZIP**. For a disposable development VM with Git:

```bash
git clone --depth 1 https://github.com/broncbash/Versionary.git
cd Versionary
git rev-parse HEAD
```

To inspect the latest guided installers without executing them:

```bash
bash -n install-versionary.sh install-versionary-agent.sh
bash install-versionary.sh --help
bash install-versionary-agent.sh --help
```

**Important:** Running those wrappers currently installs the immutable **v0.1.0-beta.1** release archives, NOT the updated server/agent source from `main`. In particular, the beta.1 server lacks the new `/api/v1/bootstrap/ca` endpoint. The agent installer can be given an independently verified local CA with `--ca-cert` until a new release is published.

## Source release-candidate preparation (developer workflow, not one-command VM setup)

The repository has a source archive builder:

```bash
python3 installer/build-versionary-release.py --output "$PWD/dist/dev"
```

It writes a versioned development archive and JSON manifest and verifies the archive. These are **local development artifacts**, not a published or signed release. They must not be mixed with the published beta.1 SHA256SUMS or passed to the current pinned wrappers. The separately packaged agent distribution must also be built and verified using the repository's release tooling before full agent acceptance testing.

## Release requirements

1. Validate source and shell syntax and run regression/security tests, including missing sudo/curl on minimal Debian and Arch.
2. Test CA fingerprint match/mismatch, discovered spoofed server, offline fallback, correct dashboard URL and service permissions.
3. Confirm actual scanner results against `checkupdates` (Arch) and `apt list --upgradable` (Debian), noting stale APT indexes can yield zero results.
4. Build a complete new server + agent release with manifest, SHA256SUMS and pinned digests; ensure wrappers target the new release.
5. Publish the prerelease, verify assets are publicly downloadable, and test on fresh disposable VMs.
6. Update README, quick-start, command reference, project status and handoff with exact release tag, digests, CLI options, known limitations, and acceptance results.

No existing beta server or agent is upgraded by merging GitHub source changes. No production approval or unattended patching is implied.
