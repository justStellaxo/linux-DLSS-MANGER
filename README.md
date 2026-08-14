# DLLS Manager

`DLLS Manager` is a CLI-first Linux prototype for discovering game installations, evaluating DLSS/NVAPI-related policy, preparing launcher mutations, applying selected changes, launching titles, and rolling those changes back.

The current codebase is beyond the original skeleton stage. It already contains working discovery adapters, policy evaluation, launch planning, mutation/rollback plumbing, a mock UI export, and regression tests. It is still an alpha prototype, not a production-ready end-user tool.

Current release-candidate target: `0.2.0a1`

## Current Status

Implemented today:

- CLI commands for detection, discovery, validation, preview, apply, launch, rollback, profile management, and override management
- Installation discovery for Steam, Faugus, Star Citizen LUG, Heroic, Lutris, Bottles, and generic `.desktop` entries
- Release-support labeling for discovered installs (`supported`, `advanced`, `experimental`)
- Policy-aware launch planning with anti-cheat and DLSS gating
- Mutation planning for DLSS runtime copy, Steam localconfig launch-option sync, and launcher sidecar sync
- Rollback manifests and rollback execution, including automatic rollback after partial apply failures and launch-start failures
- Static mock UI export backed by the same planner data model
- Regression tests for discovery, policy logic, CLI flow, snapshots, apply/launch, overrides, and release-critical failure paths

Still incomplete:

- A production-safe DLSS payload catalog with compatibility matrix and hashes
- A real UI on top of the CLI/domain layer
- Broader validation against real local installs and more launcher edge cases

## Repository Layout

```text
DLLS-Manager/
├── main.py
├── README.md
├── README_FIRST_STEPS.md
├── dlls_manager/
├── profiles/
├── fixtures/
├── mock_ui/
└── tests/
```

Important runtime/generated paths:

- `installs.json`: cached discovery report
- `snapshots/`: command snapshots
- `rollbacks/`: rollback manifests and backups
- `install_overrides/`: persisted per-install overrides
- `mock_ui/mock-library.json` and `mock_ui/mock-library.js`: generated mock UI payloads

These paths are intentionally ignored by Git.

## Quick Start

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python3 main.py --help
```

You can also run the installed console entry point:

```bash
dlls-manager --help
```

## Typical Workflow

1. Discover installs

```bash
python3 main.py discover-launchers --snapshot
python3 main.py list-installs
```

2. Inspect and validate one install

```bash
python3 main.py show-install steam:sample-dx11
python3 main.py validate-install steam:sample-dx11 --snapshot
```

3. Prepare and review the launch plan

```bash
python3 main.py prepare-launch --install-id steam:sample-dx11 --profile default --snapshot
python3 main.py explain-policy --install-id steam:sample-dx11 --profile default
```

4. Apply planned changes or do a dry-run launch

```bash
python3 main.py apply --install-id steam:sample-dx11 --profile default
python3 main.py launch --install-id steam:sample-dx11 --profile default --dry-run
```

For Steam-backed installs, launcher sync is now explicit opt-in. When enabled, DLLS Manager writes launch options into Steam's `localconfig.vdf`; if Steam is already running, restart Steam before expecting those changes to apply.

5. Roll back changes if needed

```bash
python3 main.py list-rollbacks
python3 main.py show-rollback <rollback-id>
python3 main.py rollback <rollback-id>
```

## CLI Commands

The current CLI surface includes:

- `detect`
- `list-games`
- `discover-launchers`
- `list-installs`
- `show-install`
- `validate-install`
- `launch-preview`
- `explain-policy`
- `export-mock-ui-data`
- `refresh-dlss-catalog`
- `list-dlss-catalog`
- `show-dlss-version`
- `download-dlss`
- `list-profiles`
- `show-profile`
- `update-profile`
- `show-install-override`
- `update-install-override`
- `prepare-launch`
- `apply`
- `launch`
- `list-rollbacks`
- `show-rollback`
- `rollback`

Run `python3 main.py --help` for the full command list and flags.

## Alpha Support Boundary

The first release candidate should be treated as a CLI-first alpha with explicit adapter tiers:

- `advanced`: Steam, Faugus, Star Citizen LUG
- `experimental`: Heroic, Lutris, Bottles, generic `.desktop` imports, and manual/generic paths

`list-installs` and `prepare-launch` surface this release-support level directly so the CLI reflects the release boundary instead of hiding it in docs only.

## Testing

The project now uses both `unittest` for the Python domain layer and `pytest` + Playwright for the live web UI.

```bash
python3 -m unittest discover -s tests -v
.venv/bin/pytest tests_e2e -q
```

Coverage map and current residual-risk notes:

- [TEST_MATRIX.md](TEST_MATRIX.md)

Install the browser runtime for Playwright once per machine:

```bash
.venv/bin/python -m playwright install chromium
```

## Real UI

The primary frontend is now the real local web UI served directly from the Python backend. It persists profile and override changes, executes discovery/catalog/apply/launch/rollback jobs, and is covered by browser tests.

Start it from the project root:

```bash
python3 main.py serve-ui --host 127.0.0.1 --port 8000
```

Then open:

```text
http://127.0.0.1:8000/
```

The UI covers:

- live library/install inspection
- validate, explain-policy, prepare, dry-run, apply, launch
- profile editing with persistence
- install override editing with persistence
- DLSS catalog refresh and managed downloads
- rollback inspection and execution
- live system capability reporting

## Legacy Mock UI

The old exported mock frontend still exists in `mock_ui/` for comparison and design fallback.

Refresh the legacy export:

```bash
python3 main.py export-mock-ui-data
```

Serve it locally:

```bash
python3 -m http.server 8080
```

Then open:

```text
http://localhost:8080/mock_ui/
```

## DLSS Catalog And Downloads

The DLSS catalog is now sourced from the official `NVIDIA/DLSS` GitHub releases feed and stored in `dlss_versions.json`.

Typical catalog workflow:

```bash
python3 main.py refresh-dlss-catalog
python3 main.py list-dlss-catalog
python3 main.py show-dlss-version 3.7.10
python3 main.py download-dlss 3.7.10
```

What `download-dlss` does:

- downloads the official Windows SDK ZIP from the matching NVIDIA release
- stores the original archive under `dlss_downloads/<version>/`
- extracts `nvngx_dlss.dll` into `dlss_runtime/<version>/`
- writes download metadata alongside the extracted runtime

This means the existing mutation/apply flow can resolve downloaded DLSS runtimes without needing fixture files.

## Safety Notes

- This project is not a driver-profile editor and does not claim universal DLSS override support.
- Unsupported-game override paths may be allowed, warned, ignored by the runtime, or blocked.
- Anti-cheat-sensitive titles should be treated conservatively and validated per title.
- `launch --dry-run` resolves planning without mutating files.
- If `apply` fails after partially changing files, the tool now attempts automatic rollback immediately.
- If `launch` fails to start after a successful `apply`, the tool now attempts automatic rollback immediately.
- The current implementation is designed for controlled local testing, not broad production deployment.

## Roadmap

Near-term work:

- harden DLSS runtime validation with compatibility metadata and payload integrity checks
- expand real-install validation and edge-case fixtures
- replace the mock UI with a thin real frontend over the existing backend logic

Detailed implementation plan for replacing the mock UI and introducing full browser automation:

- [REAL_UI_AND_PLAYWRIGHT_PLAN.md](REAL_UI_AND_PLAYWRIGHT_PLAN.md)

## DLSS Catalog Plan

The next major gap is a production-safer DLSS payload catalog and download-manager layer.

Planned direction:

- use official NVIDIA DLSS and Streamline releases as the default remote catalog sources
- track NVIDIA App as an official supported update path, but not as a generic per-version DLL archive
- support local extraction from already installed games as a first-class source type
- keep community mirrors disabled by default and require explicit opt-in plus checksum/signature verification
- separate `download` from `apply` so no payload swap happens implicitly
- record provenance, hashes, verification state, compatibility state, and rollback metadata for every payload

Detailed implementation plan:

- [DLSS_CATALOG_DOWNLOAD_PLAN.md](DLSS_CATALOG_DOWNLOAD_PLAN.md)

Initial source policy:

- Official NVIDIA sources first:
  - `NVIDIA/DLSS` GitHub releases
  - `NVIDIA-RTX/Streamline` GitHub releases
  - NVIDIA developer pages for DLSS and Streamline
- Official end-user path:
  - NVIDIA App DLSS overrides for supported titles
- Optional mirrors later:
  - community archives such as TechPowerUp, but only as opt-in mirror providers

## Release Plan

The project also has a separate release plan for turning the current prototype into a first publishable alpha.

- [RELEASE_VERSION_PLAN.md](RELEASE_VERSION_PLAN.md)
- [RELEASE_NOTES_0.2.0a1.md](RELEASE_NOTES_0.2.0a1.md)
- [VALIDATION_REPORT_0.2.0a1.md](VALIDATION_REPORT_0.2.0a1.md)
