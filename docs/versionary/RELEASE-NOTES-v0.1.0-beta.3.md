# Versionary v0.1.0-beta.3

## Release purpose

Correct the public agent installation packaging defect found
during live beta.2 testing.

## Confirmed beta.2 results

- Arch Linux agent installed successfully using a manually
  reconstructed, verified distribution.
- Administrator approval and secure enrollment succeeded.
- Heartbeat and initial update report succeeded.
- Daily observer-only reporting timer enabled.
- No system package updates installed.
- Server remained operational.

## Installer correction

The beta.2 public installer downloaded a raw agent archive
and incorrectly supplied it as a complete distribution.

The corrected installer:

- Uses the checksum-verified release assets.
- Stages the raw agent archive.
- Builds the complete agent distribution.
- Verifies distribution integrity.
- Supplies the complete distribution to the guided installer.
- Rebuilds rather than trusting a previously cached distribution.

## Security

- Administrator approval remains mandatory.
- Production deployment remains disabled.
- Agent reporting does not install package updates.
- Existing beta.2 release assets remain unchanged.

## Required release acceptance

- Build beta.3 source archive and manifest.
- Build and verify beta.3 agent asset.
- Generate and verify SHA256SUMS.
- Update installer version and checksum pin.
- Verify public installer against final release assets.
- Complete regression testing.
- Publish immutable beta.3 release assets.
- Test fresh Debian installation.

## Status

Release candidate preparation only.
Not yet published.
