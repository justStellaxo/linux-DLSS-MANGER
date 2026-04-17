# Prototype Version Plan

## Goal

Build a prototype release that is strong enough to validate the core product idea end to end:

- detect local system/runtime capabilities
- load game and profile metadata
- classify anti-cheat risk automatically where possible
- generate a policy-aware launch plan
- show the result in both CLI output and a mock UI
- persist snapshots for inspection

This prototype is not the final product. It is meant to answer these questions:

1. Can the tool model per-game DLSS/NVAPI override intent safely?
2. Can it detect enough anti-cheat/runtime context to make conservative decisions?
3. Can the same planning result drive both CLI and UI views?
4. Can the project be tested without touching live protected games?

---

## Prototype scope

## In scope

- CLI commands for detection, listing, preview, and policy explanation
- JSON-driven game/profile databases
- automatic anti-cheat signal detection from metadata and filesystem markers
- anti-cheat policy engine with `verified_supported`, `warn`, and `blocked`
- DLSS version selection intent in the data model
- unsupported-game override intent in the data model
- static mock UI that renders library, game details, warnings, and launch preview from JSON
- snapshot files for launch plans and policy decisions
- tests for core planner, anti-cheat policy, and mock UI data flow

## Out of scope for the prototype

- real DLL/runtime swapping
- real Steam launch-option mutation
- direct game launch against live multiplayer titles
- Heroic/Lutris adapters
- production-grade desktop packaging
- cloud sync or community profile sharing

The prototype should default to conservative behavior:

- if anti-cheat status is uncertain, warn or block
- if a DLSS path is not verified, do not claim it works
- if a mock UI action implies a blocked policy, show the block reason instead of simulating success

---

## Prototype user flows

## Flow 1: Capability detection

User runs:

```bash
python3 main.py detect
```

Result:

- normalized system capability report
- raw command output for debugging
- derived flags such as `steam_available`, `vulkan_available`, `smooth_motion_supported`

## Flow 2: Library listing

User runs:

```bash
python3 main.py list-games
```

Result:

- game list
- anti-cheat vendor and policy
- basic override capability flags

## Flow 3: Launch preview with policy gating

User runs:

```bash
python3 main.py launch-preview <game_id> --profile <profile>
```

Result:

- merged launch plan
- requested override features
- anti-cheat assessment
- `ok`, `warn`, or `blocked` compatibility status
- structured warnings and blocked reasons

## Flow 4: Mock UI inspection

User opens a static HTML page and can:

- browse sample games
- pick a profile
- view launch preview JSON
- see anti-cheat and compatibility decisions
- compare `verified_supported` vs `warn` vs `blocked` titles visually

---

## Proposed repository layout

The prototype should evolve the current repository into this structure:

```text
DLLS-Manager/
├── main.py
├── README_FIRST_STEPS.md
├── LINUX_NVIDIA_APP_LIKE_MANAGER_PLAN.md
├── PROTOTYPE_VERSION_PLAN.md
├── games.json
├── anti_cheat_rules.json
├── dlss_versions.json
├── profiles/
│   ├── default.json
│   ├── safe.json
│   └── experimental.json
├── fixtures/
│   ├── game_dirs/
│   │   ├── eac_sample/
│   │   ├── battleye_sample/
│   │   └── no_anticheat_sample/
│   └── plans/
│       ├── expected_ok.json
│       ├── expected_warn.json
│       └── expected_blocked.json
├── dlls_manager/
│   ├── __init__.py
│   ├── cli.py
│   ├── detector.py
│   ├── models.py
│   ├── game_db.py
│   ├── profile_db.py
│   ├── anti_cheat.py
│   ├── dlss_policy.py
│   ├── launch_plan.py
│   ├── snapshots.py
│   ├── mock_data.py
│   └── utils.py
├── mock_ui/
│   ├── index.html
│   ├── styles.css
│   ├── app.js
│   └── mock-library.json
└── tests/
    ├── test_detector.py
    ├── test_game_db.py
    ├── test_profile_db.py
    ├── test_anti_cheat.py
    ├── test_dlss_policy.py
    ├── test_launch_plan.py
    ├── test_snapshots.py
    └── test_mock_ui_data.py
```

---

## Relevant files and responsibilities

## Root files

### `main.py`

- thin entry point only
- delegates to `dlls_manager.cli`

### `games.json`

- prototype library records
- includes runtime, anti-cheat metadata, override support flags

### `anti_cheat_rules.json`

- rule table for automatic detection and default policy mapping
- includes marker files, vendor names, default policy class, and notes

Example structure:

```json
[
  {
    "vendor": "EasyAntiCheat",
    "markers": ["EasyAntiCheat", "EasyAntiCheat_EOS_Setup.exe"],
    "default_policy": "blocked",
    "notes": "Conservative default for experimental override paths."
  }
]
```

### `dlss_versions.json`

- whitelist of known selectable DLSS runtime labels for the prototype
- metadata only; no automatic binary swapping in prototype

Example structure:

```json
[
  {
    "id": "game_default",
    "label": "Game Default",
    "selectable": true
  },
  {
    "id": "2.5.1",
    "label": "DLSS 2.5.1",
    "selectable": true
  }
]
```

## `profiles/*.json`

- profile presets for safe/default/experimental behavior
- should include:
  - `enable_nvapi`
  - `enable_smooth_motion`
  - `dlss_mode`
  - `dlss_version`
  - `allow_unsupported_override`
  - `safety_mode`

## Python package files

### `dlls_manager/models.py`

- typed dataclasses or typed dictionaries for:
  - `GameRecord`
  - `Profile`
  - `SystemCapabilities`
  - `LaunchPlan`
  - `PolicyDecision`
  - `SnapshotRecord`

### `dlls_manager/game_db.py`

- load and validate `games.json`
- enrich missing defaults
- reject malformed records early

### `dlls_manager/profile_db.py`

- load and validate profiles
- expose preset names and merged defaults

### `dlls_manager/detector.py`

- wraps system command detection
- returns normalized capability structure
- may later support scanning local game directories

### `dlls_manager/anti_cheat.py`

- automatic anti-cheat detection
- scans metadata and optional filesystem markers
- maps results to `verified_supported`, `warn`, or `blocked`
- exposes explanation strings for CLI and UI

### `dlls_manager/dlss_policy.py`

- validate requested DLSS mode/version against game/runtime support
- downgrade unsupported requests to warning or block

### `dlls_manager/launch_plan.py`

- merge game, profile, detector, anti-cheat, and DLSS policy data
- output a deterministic launch plan

### `dlls_manager/snapshots.py`

- persist preview results as JSON
- save timestamped records under a local snapshots directory

### `dlls_manager/mock_data.py`

- convert internal `LaunchPlan` objects into JSON consumed by the mock UI

### `dlls_manager/cli.py`

- defines commands:
  - `detect`
  - `list-games`
  - `launch-preview`
  - `explain-policy`
  - `export-mock-ui-data`

## Mock UI files

### `mock_ui/index.html`

- static shell for prototype interface
- library panel
- selected game panel
- profile selector
- policy result card
- raw preview JSON panel

### `mock_ui/styles.css`

- visual treatment for statuses:
  - green for `ok`
  - amber for `warn`
  - red for `blocked`

### `mock_ui/app.js`

- loads `mock-library.json`
- renders sample game entries
- updates details and plan preview
- does not mutate the system

### `mock_ui/mock-library.json`

- exported UI-facing sample data
- can be generated from CLI using `export-mock-ui-data`

---

## Anti-cheat prototype design

## Detection signals

The prototype should use conservative multi-signal detection:

1. Explicit metadata in `games.json`
2. Marker files or directories in a scanned game folder
3. Runtime hints such as launcher type and game notes

Example marker ideas:

- `EasyAntiCheat`
- `EasyAntiCheat_EOS_Setup.exe`
- `BEService.exe`
- `BattlEye`
- known anti-cheat launcher arguments or config paths

## Decision model

The anti-cheat engine should compute:

- `vendor`
- `confidence`
- `policy`
- `reasons`
- `safe_actions`
- `blocked_actions`

### Example safe actions

- plain metadata inspection
- launch preview generation
- non-mutating profile selection in mock UI

### Example blocked actions

- unsupported override attempts on `blocked` titles
- DLSS runtime swap intent on protected multiplayer titles
- Smooth Motion or presentation overrides on unverified anti-cheat titles

## Policy classes

### `verified_supported`

- anti-cheat-sensitive title, but prototype has an explicit documented safe path
- still no binary swapping in prototype

### `warn`

- title may be single-player, unknown, or insufficiently verified
- preview allowed
- mock UI can show suggested safe subset only

### `blocked`

- anti-cheat-sensitive or high-risk title
- preview allowed
- any experimental override path shown as blocked

## Prototype behavior rules

1. Detection failure never upgrades a game to safe.
2. Unknown anti-cheat plus experimental override intent becomes at least `warn`.
3. High-risk multiplayer titles default to `blocked`.
4. Mock UI must display why something is blocked, not just that it is blocked.
5. The prototype should not claim parity with NVIDIA App anti-cheat behavior.

---

## Mock UI plan

## Purpose

The mock UI exists to validate interaction design and decision clarity before building a real desktop app.

## Required screens

### 1. Library screen

- list of sample games
- anti-cheat badge
- override support badge
- current policy color

### 2. Game detail screen

- game metadata
- selected profile
- requested features
- anti-cheat reasoning
- compatibility status

### 3. Launch preview screen

- env vars
- wrappers
- warnings
- blocked reasons
- snapshot/export button mock

## Required UI states

- no game selected
- safe preview
- warning preview
- blocked preview
- detection failure state

## Mock UI implementation choice

Use plain HTML/CSS/JS for the prototype because:

- no framework bootstrapping overhead
- easy to inspect locally
- data can be exported directly from Python
- keeps focus on planner behavior rather than frontend tooling

---

## CLI commands for the prototype

These should exist by the end of the prototype:

```bash
python3 main.py detect
python3 main.py list-games
python3 main.py launch-preview sample-dx11 --profile default
python3 main.py explain-policy sample-dx12 --profile experimental
python3 main.py export-mock-ui-data
```

### `explain-policy`

- prints anti-cheat inputs
- prints DLSS policy inputs
- prints final allow/warn/block reasoning

### `export-mock-ui-data`

- writes `mock_ui/mock-library.json`
- exports a small set of sample plans for UI rendering

---

## Snapshot strategy

Prototype snapshots should be JSON files under a local directory, for example:

```text
snapshots/
├── detect-2026-04-15T120000.json
├── preview-sample-dx11-default.json
└── preview-sample-dx12-experimental.json
```

Each snapshot should contain:

- command name
- input references
- generated plan
- policy decision
- timestamp

This gives traceability without adding a database.

---

## Implementation phases

## Phase 0: Refactor foundation

Deliverables:

- create `dlls_manager/` package
- move validation and planner logic out of `main.py`
- keep CLI behavior unchanged

Definition of done:

- current commands still run
- code paths are modular enough to unit test

## Phase 1: Anti-cheat-aware planner

Deliverables:

- add `anti_cheat_rules.json`
- add automatic marker-based anti-cheat detection
- add `explain-policy` command
- ensure launch preview includes policy reasoning

Definition of done:

- preview returns `ok`, `warn`, or `blocked`
- anti-cheat reasons are visible in CLI output
- unknown titles default conservatively

## Phase 2: DLSS policy modeling

Deliverables:

- add `dlss_versions.json`
- validate `dlss_version` and `allow_unsupported_override`
- distinguish supported vs experimental vs blocked requests

Definition of done:

- invalid DLSS selections are rejected or downgraded deterministically
- policy output explains why

## Phase 3: Mock UI

Deliverables:

- static `mock_ui/` files
- export data from planner to UI JSON
- render safe/warn/blocked states

Definition of done:

- UI loads locally without backend
- sample library reflects planner output faithfully

## Phase 4: Snapshots and polish

Deliverables:

- snapshot writer
- more fixture data
- improved error messages

Definition of done:

- any preview or exported UI data can be reproduced from fixtures

---

## Testing strategy

## Test goals

The test suite should prove:

1. malformed data is rejected cleanly
2. policy decisions are deterministic
3. anti-cheat detection fails safely
4. mock UI data matches planner output
5. no test depends on a real protected online game

## Unit tests

### `test_game_db.py`

- valid game record loads
- missing required fields fail
- invalid `anti_cheat_policy` fails

### `test_profile_db.py`

- valid profile loads
- invalid `safety_mode` fails
- `dlss_version` and override flags normalize correctly

### `test_detector.py`

- command absence handled safely
- parser handles stderr output
- derived flags are stable

### `test_anti_cheat.py`

- EAC markers map to expected vendor
- BattlEye markers map to expected vendor
- unknown markers fall back conservatively
- blocked titles reject experimental requests

### `test_dlss_policy.py`

- supported DLSS selection returns `ok`
- unsupported version selection returns `warn` or `blocked`
- unsupported-game override intent is downgraded appropriately

### `test_launch_plan.py`

- merge order is deterministic
- `requested_features` are correct
- warnings and block reasons are preserved

### `test_snapshots.py`

- snapshot files serialize correctly
- timestamps and payload fields exist

### `test_mock_ui_data.py`

- exported JSON contains all required UI fields
- status colors or status labels map consistently

## Fixture-based tests

Use sample directories under `fixtures/game_dirs/` to simulate:

- Easy Anti-Cheat title
- BattlEye title
- no anti-cheat title
- malformed/ambiguous title

These tests should never launch a real game. They only scan markers and metadata.

## Integration tests

Run CLI commands against fixtures:

```bash
python3 main.py list-games
python3 main.py launch-preview sample-dx11 --profile default
python3 main.py explain-policy sample-dx12 --profile experimental
python3 main.py export-mock-ui-data
```

Assertions:

- commands exit cleanly
- generated JSON is valid
- blocked titles stay blocked
- mock UI export includes matching policy decisions

## UI verification

For the static mock UI, test at two levels:

1. Data contract tests
   - verify `mock-library.json` schema

2. Browser smoke tests
   - page loads
   - sample game selection changes detail panel
   - blocked game shows blocked reason

If a browser automation layer is added later, Playwright is a good fit. For the prototype, schema tests plus one simple smoke test are sufficient.

## Regression strategy

Keep three canonical golden cases:

- one `ok` title
- one `warn` title
- one `blocked` title

Their exported launch plans should be kept under fixtures and compared in tests so that policy drift is obvious.

---

## Prototype acceptance criteria

The prototype is complete when all of these are true:

1. CLI commands produce deterministic, policy-aware launch previews.
2. Anti-cheat detection can infer vendor/policy from metadata or markers for sample fixtures.
3. Unknown or risky titles default to conservative output.
4. DLSS version selection exists as validated metadata and policy, even if no real binary swapping occurs.
5. Mock UI displays the same planner result as the CLI.
6. Snapshot files can be generated and inspected.
7. Tests cover `ok`, `warn`, and `blocked` paths without touching real protected games.

---

## Recommended build order

1. Refactor into `dlls_manager/` modules.
2. Add `anti_cheat_rules.json` and automatic policy detection.
3. Add `explain-policy`.
4. Add `dlss_versions.json` and DLSS policy validation.
5. Add snapshot export.
6. Add `export-mock-ui-data`.
7. Build static `mock_ui/`.
8. Add fixture and regression tests.
