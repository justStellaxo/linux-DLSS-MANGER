# Validation Report: 0.2.0a1

Date: 2026-04-17  
Scope: non-destructive release-candidate validation

## Automated Validation

Completed locally:

- `python3 -m unittest discover -s tests -v`
- repeated full-suite runs with all tests green
- editable install into a fresh virtual environment
- installed entry point verification via `dlls-manager --help`

Observed final automated status:

- `40/40` tests passing
- package installs as `dlls-manager 0.2.0a1`

## Local Non-Destructive Adapter Validation

These checks intentionally avoided `apply` on real user installs.

### Faugus / Battle.net

Commands checked:

- `python3 main.py validate-install faugus:battlenet`
- `python3 main.py prepare-launch --install-id faugus:battlenet --profile default`
- `python3 main.py launch --install-id faugus:battlenet --profile default --dry-run`

Observed result:

- validation succeeded
- one warning present:
  - referenced `addapp_bat` path was missing
- prepare/dry-run completed
- release support level: `advanced`
- compatibility status: `warn`

Observed warnings:

- anti-cheat context stayed conservative
- install is not marked as supporting DLSS/NVAPI override workflows

Interpretation:

- discovery and planning work on the live adapter path
- launcher metadata import is usable
- the missing `addapp_bat` reference is a real local-data warning, not a parser failure

### Star Citizen LUG

Commands checked:

- `python3 main.py validate-install starcitizen_lug:star-citizen`
- `python3 main.py prepare-launch --install-id starcitizen_lug:star-citizen --profile default`
- `python3 main.py launch --install-id starcitizen_lug:star-citizen --profile default --dry-run`

Observed result:

- validation succeeded without errors
- prepare/dry-run completed
- release support level: `advanced`
- compatibility status: `warn`

Observed warnings:

- anti-cheat context stayed conservative
- install is not marked as supporting DLSS/NVAPI override workflows

Interpretation:

- script-based discovery and planning worked against the live local setup
- wrapper/script/runner resolution is functioning on the current machine

## What Was Not Done Automatically

For safety reasons, these were not executed against real installs as part of the automated release-candidate pass:

- `apply` on live user game installs
- live game process launch with mutations
- rollback on live user game installs after real mutation

Those paths are covered by fixture/integration tests in the automated suite and should still be manually exercised only when you want to validate a specific real install deliberately.

## Release Assessment

Based on the current code, tests, and non-destructive live checks:

- `Steam` is the strongest release path
- `Faugus` and `Star Citizen LUG` are credible `advanced` alpha paths
- `Heroic`, `Lutris`, `Bottles`, and generic desktop imports should remain `experimental`
