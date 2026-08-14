# Real UI And Playwright Plan

## Goal

Replace the current static `mock_ui/` export with a real local web application backed by the existing Python domain layer, then add browser automation that covers every user-facing control and every critical workflow end to end.

This plan is intentionally technical and implementation-oriented. It is meant to be executed in phases, not treated as a loose roadmap.

## Current State

The repository currently has:

- a working CLI/domain layer for discovery, validation, policy, launch planning, apply, launch, rollback, profile management, install overrides, and DLSS catalog downloads
- a static Steam-inspired GUI in `mock_ui/`
- no live HTTP backend
- no browser automation
- no guarantee that every CLI workflow is reachable from the GUI

The gap to close is not visual. The real missing pieces are:

- live backend endpoints
- durable job execution for long-running actions
- bidirectional persistence from UI controls into profiles/overrides/actions
- end-to-end tests that verify actual side effects, not only rendered text

## Non-Goals

These items should not block the first real UI release:

- native desktop packaging
- authentication or multi-user support
- remote deployment
- websocket-heavy reactive dashboards
- frontend framework migration for its own sake

## Target Architecture

### Architecture Summary

Use a local Python web application with a JSON API and static frontend assets.

Recommended stack:

- `FastAPI` for HTTP API and static file serving
- `uvicorn` for local runtime
- plain HTML/CSS/ES modules for the frontend
- Python Playwright for end-to-end testing

Do not build the UI by shelling out to `python3 main.py ...` from HTTP handlers. The web layer should import and call the existing domain functions directly.

### Runtime Model

The real UI should run as:

```text
browser
  -> local HTTP server
    -> JSON API
      -> existing dlls_manager domain layer
```

Long-running actions should run as jobs:

- discovery
- validate
- prepare
- catalog refresh
- DLSS download
- apply
- launch
- rollback

The UI should poll job state over HTTP. Websockets are optional later, not required for the first implementation.

## Proposed Repository Layout

```text
dlls_manager/
├── webapp/
│   ├── __init__.py
│   ├── app.py
│   ├── routes_bootstrap.py
│   ├── routes_installs.py
│   ├── routes_profiles.py
│   ├── routes_overrides.py
│   ├── routes_dlss.py
│   ├── routes_rollbacks.py
│   ├── routes_jobs.py
│   ├── schemas.py
│   ├── jobs.py
│   ├── state.py
│   └── static/
│       ├── index.html
│       ├── catalog.html
│       ├── profiles.html
│       ├── rollbacks.html
│       ├── system.html
│       ├── app.js
│       ├── catalog.js
│       ├── profiles.js
│       ├── rollbacks.js
│       ├── system.js
│       ├── api.js
│       ├── store.js
│       └── styles.css
└── ...

tests_e2e/
├── conftest.py
├── helpers.py
├── test_library.py
├── test_install_detail.py
├── test_profiles.py
├── test_overrides.py
├── test_dlss_catalog.py
├── test_rollbacks.py
├── test_system.py
└── fixtures/
```

Transitional rule:

- keep `mock_ui/` until the real UI is feature-complete
- once the real app is stable, either remove `mock_ui/` or freeze it as a legacy demo folder

## Backend Plan

### 1. Web App Entry Point

Add a local web app module:

- `dlls_manager/webapp/app.py`

Responsibilities:

- create FastAPI app
- mount static assets
- register API routers
- expose health endpoint

Suggested commands:

```bash
python3 -m dlls_manager.webapp
python3 main.py serve-ui
```

Add a CLI command:

- `serve-ui`

This should start the local HTTP server and serve the real UI assets.

### 2. API Contract

Define stable response models in `dlls_manager/webapp/schemas.py`.

Do not leak raw domain internals everywhere. Normalize responses for UI consumption.

Required schemas:

- `BootstrapResponse`
- `SystemSummary`
- `InstallSummary`
- `InstallDetailResponse`
- `ValidationResponse`
- `LaunchPlanResponse`
- `PolicyExplanationResponse`
- `ProfileListResponse`
- `ProfileDetailResponse`
- `InstallOverrideResponse`
- `DlssCatalogResponse`
- `DlssCatalogEntryResponse`
- `RollbackListResponse`
- `RollbackDetailResponse`
- `JobResponse`
- `JobResultResponse`
- `ErrorResponse`

### 3. Bootstrap Endpoint

Add:

- `GET /api/bootstrap`

This should return:

- generated timestamp
- system capabilities summary
- profile names
- default profile
- install summaries
- selected/default install if available
- DLSS catalog summary
- rollback summary

Purpose:

- allow the UI to render initial navigation without chaining many requests
- keep the first paint predictable

### 4. Install Endpoints

Add:

- `GET /api/installs`
- `GET /api/installs/{install_id}`
- `POST /api/installs/{install_id}/validate`
- `POST /api/installs/{install_id}/prepare`
- `POST /api/installs/{install_id}/explain-policy`
- `POST /api/installs/{install_id}/apply`
- `POST /api/installs/{install_id}/launch`

Rules:

- `validate`, `prepare`, `apply`, `launch` should return a `job_id`
- sync execution is allowed only for cheap read endpoints
- the detail endpoint should include release-support level and a condensed summary for UI rendering

### 5. Profile Endpoints

Add:

- `GET /api/profiles`
- `GET /api/profiles/{profile_name}`
- `PATCH /api/profiles/{profile_name}`

Supported editable fields:

- `enable_nvapi`
- `enable_smooth_motion`
- `use_gamemode`
- `use_mangohud`
- `launch_args`
- `custom_env`
- `dlss_mode`
- `dlss_version`
- `allow_unsupported_override`
- `safety_mode`

Profile updates must reuse the existing persistence logic rather than reimplementing profile writes.

### 6. Override Endpoints

Add:

- `GET /api/installs/{install_id}/override`
- `PATCH /api/installs/{install_id}/override`

Supported fields:

- `dlss_version`
- `enable_nvapi`
- `enable_smooth_motion`
- `use_gamemode`
- `use_mangohud`
- `allow_unsupported_override`
- `launch_args`
- `extra_env`
- `extra_wrappers`
- `sync_to_launcher`
- `dlss_target_path`

### 7. DLSS Catalog Endpoints

Add:

- `GET /api/dlss/catalog`
- `GET /api/dlss/catalog/{version_id}`
- `POST /api/dlss/catalog/refresh`
- `POST /api/dlss/catalog/{version_id}/download`

Expected behavior:

- list endpoint returns all catalog entries sorted descending by version
- entry endpoint returns the full release/download state
- refresh returns a job
- download returns a job

The UI should not guess download state from local paths. That must come from the API.

### 8. Rollback Endpoints

Add:

- `GET /api/rollbacks`
- `GET /api/rollbacks/{rollback_id}`
- `POST /api/rollbacks/{rollback_id}/execute`

The detail response should expose enough context for the UI to show:

- target install
- profile
- created_at
- affected files
- current applicability state if determinable

### 9. Job System

Add `dlls_manager/webapp/jobs.py`.

Job model:

- `job_id`
- `operation`
- `status`
- `started_at`
- `finished_at`
- `input`
- `result`
- `error`

Allowed statuses:

- `queued`
- `running`
- `completed`
- `failed`

Add endpoints:

- `GET /api/jobs/{job_id}`
- `GET /api/jobs`

Implementation requirement:

- use a thread pool or background tasks for now
- keep job state in memory plus optional JSON persistence under a new runtime directory such as `web_jobs/`

### 10. Error Handling

Every route must return normalized error payloads:

```json
{
  "error": {
    "code": "validation_failed",
    "message": "Human-readable summary",
    "details": {}
  }
}
```

Playwright tests should verify these payload-driven UI error states.

## Frontend Plan

### 1. Keep The Existing Visual Direction

Reuse the current Steam-inspired direction.

The goal is not a redesign. The goal is wiring the current design to the live backend.

### 2. Frontend Pages

Required pages:

- `Library`
- `Install Detail`
- `DLSS Catalog`
- `Profiles`
- `Rollbacks`
- `System`

Optional later:

- `Known Games`
- `Debug`

### 3. Frontend State Modules

Create small focused modules:

- `api.js`
  responsibilities:
  fetch wrappers, polling helper, request normalization
- `store.js`
  responsibilities:
  selected install, selected profile, current jobs, cache invalidation
- page-specific modules

Avoid unstructured DOM mutation spread everywhere.

### 4. Required UI Controls

Library page:

- search field
- profile selector
- install list
- install refresh button
- install selection

Install detail page:

- validate button
- explain policy button
- prepare button
- dry-run launch button
- apply button
- real launch button
- override edit button
- rollback history access

Launch options panel:

- DLSS dropdown
- runner preset dropdown
- toggles for:
  - MangoHud
  - GameMode
  - NVAPI
  - smooth motion if supported
  - fallback env toggles where applicable
- launch args editor
- environment editor

DLSS catalog page:

- filter/search field
- refresh button
- per-entry detail view
- per-entry download button
- downloaded-state badge
- official release link

Profiles page:

- profile list
- create or duplicate profile later
- edit form
- save button

Rollbacks page:

- rollback list
- detail pane
- execute rollback button

System page:

- capability badges
- driver and Vulkan summary
- launcher presence summary

### 5. UI-to-Backend Binding Rule

Every button in the real UI must trigger one of:

- a GET or PATCH request
- a job-creating POST request
- a local-only view state update that is still covered by tests

No dead buttons are acceptable.

### 6. Selector Policy For Testing

Every important interactive element must have a stable `data-testid`.

Examples:

- `data-testid="library-search"`
- `data-testid="profile-select"`
- `data-testid="install-row-steam-sample-dx11"`
- `data-testid="validate-button"`
- `data-testid="prepare-button"`
- `data-testid="dry-run-button"`
- `data-testid="apply-button"`
- `data-testid="launch-button"`
- `data-testid="dlss-version-select"`
- `data-testid="dlss-download-button-3-7-10"`
- `data-testid="catalog-refresh-button"`
- `data-testid="rollback-button-<id>"`

Playwright tests must not rely on cosmetic text or layout structure when a stable test id can be used.

## Mapping Existing CLI Functions To UI

The following CLI functions must be directly reachable from the UI:

- `detect` -> `System`
- `discover-launchers` -> `Library Refresh`
- `list-installs` -> `Library`
- `show-install` -> `Install Detail`
- `validate-install` -> `Validate`
- `launch-preview` or `prepare-launch` -> `Launch Plan`
- `explain-policy` -> `Policy Panel`
- `list-profiles` and `show-profile` -> `Profiles`
- `update-profile` -> `Profiles Save`
- `show-install-override` -> `Override Panel`
- `update-install-override` -> `Override Save`
- `refresh-dlss-catalog` -> `Catalog Refresh`
- `list-dlss-catalog` and `show-dlss-version` -> `DLSS Catalog`
- `download-dlss` -> `Catalog Download`
- `apply` -> `Apply`
- `launch --dry-run` -> `Dry Run`
- `launch` -> `Launch`
- `list-rollbacks`, `show-rollback`, `rollback` -> `Rollbacks`

Acceptance rule:

- if a CLI workflow is considered release-critical, it must exist in the UI before the mock UI can be retired

## Playwright Introduction Plan

### Tooling

Use Python Playwright so it fits the existing repo and test stack.

Dependencies:

- `playwright`
- `pytest` or `unittest` wrapper for E2E; `pytest` is preferable for fixtures

Browser install:

```bash
python3 -m playwright install chromium
```

### E2E Test Environment

The E2E suite must run the real web app against isolated runtime directories.

Environment override targets:

- `installs.json`
- `snapshots/`
- `rollbacks/`
- `install_overrides/`
- `dlss_runtime/`
- `dlss_downloads/`
- optional `web_jobs/`

Do not let E2E mutate the developer's real runtime files.

### API Mocking Policy In E2E

External NVIDIA network calls should not be required for every test.

Strategy:

- use a local fixture catalog for most tests
- have one explicit integration-marked test for live refresh if desired
- use local ZIP fixtures for `download-dlss` tests

### E2E Coverage Requirement

Every visible button and every user-visible save/apply action must have:

- render test
- click test
- success-path assertion
- failure-path assertion where applicable

### Minimum Screen Test Matrix

Library:

- page loads bootstrap successfully
- search filters installs
- profile switch updates active install detail
- refresh button updates install list
- clicking install row updates detail panel

Install detail:

- validate button produces completed job and updates validation view
- explain policy button shows policy reasons
- prepare button shows latest launch plan
- dry-run button creates a non-mutating launch result
- apply button creates rollback metadata
- launch button creates launch job and reflects result

Overrides:

- changing DLSS dropdown persists override
- changing MangoHud toggle persists override
- changing GameMode toggle persists override
- changing NVAPI toggle persists override
- changing launch args persists override
- changing custom env persists override

Profiles:

- list loads all profiles
- editing a profile saves and changes subsequent prepare results
- invalid profile edit returns error state

DLSS catalog:

- catalog page lists all entries sorted descending
- search filters entries
- refresh button updates the catalog job state
- download button downloads a runtime
- downloaded badge updates after job completion
- install detail DLSS dropdown reflects downloaded version

Rollbacks:

- rollback list loads
- rollback detail loads
- rollback execute button restores state
- rollback failure is rendered clearly

System:

- capabilities render
- missing capability state renders correctly when fixture says unavailable

### Per-Button Test Inventory

This should be tracked as an explicit checklist during implementation:

- `Library Refresh`
- `Install row`
- `Validate`
- `Explain Policy`
- `Prepare Launch`
- `Dry Run`
- `Apply`
- `Launch`
- `Save Override`
- `Save Profile`
- `Catalog Refresh`
- `Catalog Download`
- `Rollback Execute`
- navigation tabs and page links

If a new button is introduced later, add a Playwright test in the same change.

## CI Plan

Add a second CI job after unit tests:

- install Python deps
- install Playwright Chromium
- start the local web app against test fixtures
- run E2E suite

Recommended split:

- `unit-tests`
- `e2e-playwright`

The E2E job should upload screenshots or traces on failure.

## Implementation Phases

### Phase 1: Backend Scaffolding

Deliverables:

- `serve-ui` command
- FastAPI app
- bootstrap endpoint
- job registry
- static asset serving

Acceptance:

- browser can load `/`
- `GET /api/bootstrap` works
- no mock JSON export is required for the page shell

### Phase 2: Library And Install Detail

Deliverables:

- live library page
- live install detail page
- validate, explain, prepare, dry-run actions

Acceptance:

- selected install and selected profile drive live backend requests
- detail page shows real planner data
- Playwright covers library navigation and detail actions

### Phase 3: Profiles And Overrides

Deliverables:

- live profile editor
- live install override editor
- DLSS dropdown persistence

Acceptance:

- editing via UI changes backend state
- prepare/validate results reflect saved edits
- Playwright verifies save + effect, not save alone

### Phase 4: DLSS Catalog

Deliverables:

- live catalog page
- refresh job
- download job
- catalog-to-library integration

Acceptance:

- downloaded entries become visible as downloaded in both catalog and library detail
- Playwright verifies catalog refresh and download flow

### Phase 5: Apply, Launch, Rollback

Deliverables:

- apply button
- launch button
- rollback page and rollback action

Acceptance:

- apply creates rollback data
- launch dry-run remains non-mutating
- rollback restores previous state
- Playwright verifies file side effects where applicable

### Phase 6: Remove Mock Dependence

Deliverables:

- `mock_ui/` retired or explicitly marked legacy
- `export-mock-ui-data` no longer required for normal UI usage

Acceptance:

- recommended UI startup path is only `serve-ui`
- documentation and tests no longer depend on mock export

## Risks To Manage

### Job State Drift

If UI and backend disagree about job completion, the app will feel broken.

Mitigation:

- stable job schema
- polling with final terminal states
- explicit result payloads

### Hidden CLI Assumptions

Some domain code may assume CLI-only flows.

Mitigation:

- create API-oriented wrappers where needed
- avoid duplicating business logic in route handlers

### E2E Flakiness

Browser tests can become unreliable if they wait on visual timing.

Mitigation:

- test IDs everywhere
- poll for job completion in deterministic ways
- no reliance on animation timing

### Unsafe Live Actions

Real `apply` and `launch` actions can mutate files.

Mitigation:

- run E2E on isolated fixture directories
- keep real-user runtime paths out of the test environment

## Definition Of Done

The mock UI can be considered replaced only when all of the following are true:

- the recommended UI entry point is the real web app, not `export-mock-ui-data`
- all release-critical CLI workflows are available from the UI
- every visible button in the real UI has Playwright coverage
- every destructive action has success and failure path tests
- DLSS catalog refresh and download work through the UI
- apply, launch, dry-run, and rollback work through the UI
- CI runs both unit tests and Playwright tests successfully

## Immediate Next Tasks

1. Add `FastAPI` and `uvicorn` to project dependencies.
2. Introduce `dlls_manager/webapp/app.py` and `serve-ui`.
3. Build `GET /api/bootstrap`.
4. Port the current `mock_ui/` library page to live API calls.
5. Add first Playwright smoke test for page load, install selection, and prepare action.
