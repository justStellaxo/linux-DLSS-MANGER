# Test Matrix

This document describes which project areas are covered by which test layer and what residual risks still exist.

## Test Layers

- `unittest` in [tests](/home/stella/PycharmProjects/DLLS-Manager/tests)
  Covers Python domain logic, CLI flows, discovery adapters, mutations, rollback handling, catalog parsing, and persistence helpers.
- `pytest` API/E2E fixtures in [tests_e2e/test_api.py](/home/stella/PycharmProjects/DLLS-Manager/tests_e2e/test_api.py)
  Covers the live FastAPI app, background jobs, job persistence, and filesystem side effects through an isolated fixture server.
- `pytest` + Playwright in [tests_e2e/test_playwright_ui.py](/home/stella/PycharmProjects/DLLS-Manager/tests_e2e/test_playwright_ui.py)
  Covers the real browser UI against a running `serve-ui` backend.

## Coverage By Area

### Discovery

- `unittest`
  - desktop entry discovery
  - Faugus import
  - Star Citizen LUG import
  - Heroic import
  - Lutris import
  - Bottles import and fallback behavior
- `pytest API`
  - live install refresh job
  - isolated desktop-entry discovery through fixture data
- `Playwright`
  - refresh button in the Library view updates visible installs

Residual risk:
- real user environments with malformed third-party launcher files still need broader fixture growth over time.

### Profiles

- `unittest`
  - profile validation
  - profile persistence updates
- `pytest API`
  - valid update roundtrip
  - invalid payload rejection
- `Playwright`
  - profile selection
  - profile save through real UI
  - persisted changes verified on disk

Residual risk:
- no browser coverage yet for every invalid profile field combination.

### Install Overrides

- `unittest`
  - override validation
  - override persistence updates
- `pytest API`
  - override roundtrip
  - invalid payload rejection
- `Playwright`
  - override save in Library view
  - persisted DLSS/env/args changes verified on disk

Residual risk:
- not every nullable override field has its own browser regression yet.

### DLSS Catalog And Downloads

- `unittest`
  - catalog sorting
  - local download state enrichment
  - ZIP extraction
- `pytest API`
  - refresh job
  - download job
  - invalid version failure job
  - downloaded runtime verified on disk
- `Playwright`
  - catalog search
  - version selection
  - refresh button
  - download button
  - downloaded state rendered after completion

Residual risk:
- malformed ZIP and malformed remote release feed are covered at the domain/helper layer, not yet with separate browser-visible error fixtures.

### Policy, Prepare, Apply, Launch

- `unittest`
  - policy evaluation
  - install launch plan generation
  - dry-run behavior
  - apply behavior
  - launch behavior
  - automatic rollback on partial apply failure
  - automatic rollback on launch start failure
- `pytest API`
  - validate
  - prepare
  - apply
  - launch
  - blocked launch path
  - broken launch path
- `Playwright`
  - validate button
  - explain-policy button
  - prepare button
  - dry-run button
  - apply button
  - launch button
  - blocked launch error surfaced in UI

Residual risk:
- browser coverage for a technical job failure path is still thinner than coverage for a policy-blocked path.

### Rollbacks

- `unittest`
  - rollback record creation
  - rollback restoration behavior
- `pytest API`
  - rollback execution after apply
- `Playwright`
  - rollback list
  - rollback detail selection
  - execute rollback button
  - restored runtime verified on disk

Residual risk:
- no dedicated browser fixture yet for a rollback manifest with partial restore errors.

### Web API And Jobs

- `pytest API`
  - `/api/health`
  - `/api/bootstrap`
  - `/api/system`
  - `/api/jobs`
  - `/api/jobs/{id}`
  - `/api/installs`
  - `/api/installs/refresh`
  - `/api/installs/{id}`
  - `/api/installs/{id}/validate`
  - `/api/installs/{id}/prepare`
  - `/api/installs/{id}/launch`
  - `/api/profiles/{name}`
  - `/api/installs/{id}/override`
  - `/api/dlss/catalog`
  - `/api/dlss/catalog/{version}/download`
  - `/api/rollbacks`
  - `/api/rollbacks/{id}`
  - `/api/rollbacks/{id}/execute`
  - startup catalog refresh job
  - failed job persistence under `web_jobs/`
  - parallel job listing

Residual risk:
- page routes themselves are mainly covered via Playwright navigation, not by a separate HTTP-only route matrix.

## Fixture Types

The current isolated E2E fixture set includes:

- `manual:test-game`
  happy-path install with working script and DLSS target
- `manual:blocked-game`
  policy-blocked install for anti-cheat/unsupported-path UI and API checks
- `manual:broken-game`
  missing-script install for launch failure coverage
- `desktop_entry:refreshed-game`
  discovery-refresh result created from a fixture desktop entry
- official-style DLSS release feed fixture
- downloadable ZIP fixtures containing `nvngx_dlss.dll`

## Current Verification Commands

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/pytest tests_e2e -q
```

## Next Expansion Targets

- add browser-visible failure fixtures for invalid catalog refresh payloads and broken ZIP downloads
- add rollback-partial-failure fixtures
- add more multi-install Library scenarios with mixed support levels and validation warnings
- add API schema/assertion helpers so response-shape drift is caught more explicitly
