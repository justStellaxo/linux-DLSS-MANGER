# Release Notes: 0.2.0a1

Date: 2026-04-17

## Summary

`0.2.0a1` is the first CLI-first alpha release candidate for `DLLS Manager`.

This candidate is aimed at controlled local testing, not broad end-user deployment.

## What Changed

- Added explicit release-support labels for discovered installs:
  - `supported`
  - `advanced`
  - `experimental`
- Hardened apply safety:
  - partial mutation failures now trigger immediate automatic rollback
- Hardened launch safety:
  - if launch startup fails after `apply`, the tool now attempts automatic rollback
- Added richer result summaries to:
  - `validate-install`
  - `prepare-launch`
  - `apply`
  - `launch`
- Added richer snapshot metadata:
  - tool version
  - install/profile context
  - compatibility summary
- Expanded regression coverage for:
  - partial apply failure rollback
  - dry-run no-mutation guarantee
  - launch-start rollback
  - release-support labeling
  - snapshot metadata
  - adapter resilience on malformed manifests
- Added packaging smoke coverage in CI for the installed console entry point

## Alpha Support Boundary

- `supported`
  - Steam
- `advanced`
  - Faugus
  - Star Citizen LUG
- `experimental`
  - Heroic
  - Lutris
  - Bottles
  - generic `.desktop` imports
  - manual/generic paths

## Safety Behavior

- `launch --dry-run` resolves planning without mutating files
- blocked policy paths still require explicit `--force`
- failed apply paths attempt immediate automatic rollback
- launch-start failures after apply attempt immediate automatic rollback

## Known Limits

- no production-grade DLSS payload catalog yet
- no real desktop UI yet
- adapter breadth still exceeds real-install validation depth
- anti-cheat-sensitive workflows still require title-level validation

## Validation State

Automated validation completed:

- full `unittest` suite passing
- repeated local runs completed
- packaging smoke verified in a fresh virtual environment

Non-destructive local validation completed:

- Faugus/Battle.net
- Star Citizen LUG

See:

- [VALIDATION_REPORT_0.2.0a1.md](VALIDATION_REPORT_0.2.0a1.md)

## Upgrade / Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
dlls-manager --help
```
