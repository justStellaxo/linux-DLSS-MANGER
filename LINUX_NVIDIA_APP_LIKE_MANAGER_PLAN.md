# Linux NVIDIA-App-Like Manager (Ubuntu) — Revised Delivery Plan

## Goal
Build a Linux manager that offers NVIDIA-App-like per-game launch controls for Proton/Wine titles, with a strong focus on safe DLSS/NVAPI-related overrides, controlled DLSS version selection where technically possible, diagnostics, and rollback.

For the Phase-2 launcher ecosystem expansion, including local Faugus/Battle.net and Star Citizen LUG findings plus wider Linux launcher research, see `PHASE2_LAUNCHER_RESEARCH_2026-04-17.md`.

The important constraint remains unchanged:

- Linux does not expose a full NVIDIA Profile Inspector equivalent for hidden Windows driver profile flags.
- The product therefore has to work as a launch orchestration and validation tool, not as a low-level driver profile editor.
- DLSS features can only be offered where the game/runtime path can actually consume them. Unsupported titles may sometimes be helped by launch-time overrides or runtime asset swaps, but this can never be treated as universally reliable.

---

## 1) Evaluation of the existing plan

## What is already good

- The technical direction is correct: Linux overrides should be assembled at launch time through environment variables, wrappers, runtime checks, and per-game policies.
- Safety concerns are treated as first-class requirements instead of an afterthought.
- The plan identifies the right major subsystems: detection, profile merge, launch planning, policy gating, execution, and diagnostics.

## Main weaknesses in the original plan

1. The scope is too wide for the current repository state.
   The codebase currently contains a small CLI MVP, sample JSON data, and no test suite. A plan that includes UI, SQLite, plugin SDK, ecosystem adapters, benchmarking, and hardware-in-loop CI too early will slow delivery.

2. The MVP boundary is not explicit enough.
   The previous plan mixed must-have launch functionality with later-stage platform features. That makes it hard to decide what “done” means for the first usable release.

3. There are no concrete acceptance criteria per phase.
   The plan lists topics, but not what observable behavior must exist before a phase is considered complete.

4. The execution and rollback path is underspecified.
   Safe mutation of Steam launch options and safe restoration are core features. They need to be promoted from “next step” to a formally defined delivery milestone.

5. UI appears too early.
   A desktop UI before the CLI core, validation engine, and rollback workflow are stable is premature.

6. The data model is named, but not shaped.
   The repository needs explicit JSON structures before introducing a database layer.

---

## 2) Current repository status

The current implementation is a CLI-first prototype with these working parts:

- basic environment detection
- a game registry loaded from `games.json`
- profile loading from `profiles/*.json`
- launch plan preview generation with env vars and wrappers

The following core product capabilities do not exist yet:

- real launch execution
- Steam launch option mutation with backup/restore
- compatibility validation
- anti-cheat policy gating
- structured logs and snapshots
- tests

This revised plan is therefore optimized for getting from “prototype” to “first safe usable CLI release”.

---

## 3) Product scope

## In scope for the first usable release

- CLI-driven workflow
- manual game records plus Steam-backed records
- deterministic launch plan generation
- Steam launch option backup and restore
- real process execution
- capability detection and compatibility checks
- anti-cheat and high-risk warning policy
- explicit unsupported-game override workflow with block/warn/allow behavior
- JSON-based snapshots, logs, and test fixtures

## Explicitly out of scope for the first usable release

- desktop GUI
- SQLite
- Heroic and Lutris support
- community profile sync
- plugin SDK
- benchmark automation
- hardware-in-loop CI

These can still be valuable later, but they should not block the first release.

---

## 4) Revised architecture

The architecture should be built in this order:

1. **Core domain layer**
   - typed game/profile/capability/launch-plan structures
   - validation and merge rules
   - no launcher-specific behavior here

2. **Capability detector**
   - detect GPU, driver, Vulkan availability, Steam presence, Proton/NVAPI prerequisites
   - normalize failures into structured capability flags instead of raw command output only

3. **Launch plan engine**
   - combine game metadata, profile settings, and runtime constraints
   - produce a deterministic `LaunchPlan`
   - expose both preview output and execution-ready command assembly
   - include optional DLSS runtime-selection inputs where supported by the game profile and execution path

4. **Steam adapter**
   - read current launch options
   - generate updated launch options
   - create snapshot backup
   - restore previous state

5. **Execution runtime**
   - execute a plan safely
   - capture stdout/stderr, exit code, timestamps
   - persist an `ExecutionResult`

6. **Safety and compatibility engine**
   - block, warn, or allow based on anti-cheat, runtime path, driver constraints, and unsupported combinations
   - distinguish between safe native settings, experimental unsupported-game overrides, and hard-blocked paths

7. **Diagnostics and snapshots**
   - persist JSON snapshots for launch plans, mutations, execution results, and restore points

8. **Additional adapters and UI**
   - only after CLI workflows are proven stable

---

## 5) Minimal data model to lock first

Before adding more features, define the JSON contract for these objects:

### `GameRecord`
- `id`
- `name`
- `launcher`
- `app_id` optional
- `runtime` such as `proton-dx11`, `proton-dx12`, `native-vulkan`
- `anti_cheat` such as `unknown`, `low`, `high`
- `anti_cheat_vendor` optional
- `anti_cheat_policy` such as `verified_supported`, `warn`, `blocked`
- `supports_dlss_override` boolean
- `supports_dlss_version_selection` boolean
- `override_mode` such as `native_only`, `experimental`, `blocked`
- `notes`

### `Profile`
- `name`
- `enable_nvapi`
- `enable_smooth_motion`
- `use_gamemode`
- `use_mangohud`
- `dlss_mode`
- `dlss_version` optional
- `allow_unsupported_override`
- `custom_env`
- `launch_args`
- `wrapper_order`
- `safety_mode`

### `SystemCapabilities`
- `gpu_present`
- `nvidia_driver_present`
- `nvidia_driver_version`
- `vulkan_available`
- `steam_available`
- `session_type`
- `proton_nvapi_supported`
- `smooth_motion_supported`
- `detector_errors`

### `LaunchPlan`
- `game_id`
- `profile_name`
- `env`
- `wrappers`
- `args`
- `command_preview`
- `dlss_version_selection`
- `override_strategy`
- `compatibility_status`
- `warnings`
- `blocked_reasons`

### `Snapshot`
- `type`
- `created_at`
- `target`
- `payload`

---

## 6) DLSS-specific feature policy

The plan now explicitly includes two distinct DLSS feature tracks:

### A. DLSS version selection

This is planned, but only as a controlled feature for execution paths where the runtime can be identified and the swap mechanism is well-defined.

Examples of what this may mean in practice:

- selecting among known DLSS runtime payloads for Proton/Wine titles
- choosing a pinned DLSS runtime version per game profile
- validating that the selected version is compatible with the game/runtime path before launch

Important limits:

- this is not the same as a universal driver-level DLSS selector
- not every title exposes or tolerates DLSS runtime swapping
- native Linux titles and some protected Windows titles may not support this path at all

### B. DLSS override for unsupported games

This is also planned, but only as an experimental workflow.

The product should classify these attempts into:

- `allowed`
- `warned`
- `blocked`

Typical supported strategy categories:

- NVAPI enablement
- launch-time environment overrides
- wrapper-based runtime shaping
- optional runtime asset selection where the title and prefix layout make it safe enough to attempt

Important limits:

- unsupported does not mean impossible, but it also does not mean reliable
- some titles will ignore the override entirely
- some titles may become unstable or trip anti-cheat protections
- high-risk games must default to warning or blocking

### C. Anti-cheat compatibility policy

Online research does not support a blanket claim that these override paths are universally anti-cheat-safe in the same way users may perceive NVIDIA App features.

The practical takeaway for this project is:

- NVIDIA frames DLSS overrides and Smooth Motion around compatible games and verified support paths, not as guaranteed-safe behavior for every protected title
- BattlEye says benign overlays are generally fine, but also documents that some files and programs can be blocked or can cause kicks depending on title policy and software behavior
- BattlEye specifically flags unexpected `d3d9.dll`, `dxgi.dll`, or `dsound.dll` files in game directories as things to remove when problems occur
- NVIDIA's Linux Smooth Motion path uses a Vulkan layer to override presentation, which should be treated as anti-cheat-sensitive until verified on a per-title basis

Therefore this manager should:

- never promise “no anti-cheat trigger like NVIDIA App” as a universal product property
- maintain per-title anti-cheat classes such as `verified_supported`, `warn`, and `blocked`
- default unknown multiplayer and anti-cheat-protected titles to warning or blocking for experimental override paths
- treat file replacement, runtime asset swapping, injected layers, and presentation overrides as high-risk unless explicitly verified
- only mark a title as low-risk after documented title-level validation

---

## 7) Revised roadmap

## Phase 0 — Stabilize the CLI core

Deliverables:

- split `main.py` into small modules
- add structured validation for `games.json` and profiles
- normalize error handling
- make `detect` return structured capability flags in addition to raw command output
- define the profile fields for `dlss_version` and `allow_unsupported_override`

Definition of done:

- malformed profile or game data produces a readable validation error
- launch plan generation is deterministic
- sample fixtures cover both valid and invalid inputs

## Phase 1 — First usable release

Deliverables:

- implement a real `launch` command
- implement a Steam adapter for launch-option generation
- implement backup and restore snapshots for Steam mutations
- add `dry-run` and `restore` commands
- carry DLSS version selection and unsupported-override intent through preview and launch planning, even if some paths still resolve to warnings or blocks

Definition of done:

- user can preview, apply, restore, and execute a launch plan from the CLI
- Steam changes are reversible
- failed mutation cannot silently leave state half-written

## Phase 2 — Safety and compatibility gating

Deliverables:

- anti-cheat policy table
- compatibility rules for runtime/profile combinations
- block/warn/allow decision engine
- explanation messages attached to each launch plan
- compatibility rules for `dlss_version` selection and unsupported-game override attempts
- verified-title policy for anti-cheat-sensitive games, with conservative defaults for unknown titles

Definition of done:

- high-risk games cannot be launched without an explicit override path
- unsupported profile/runtime combinations are rejected before execution
- user sees why a plan is blocked or downgraded
- DLSS version selection is rejected cleanly when the game/runtime path does not support it
- anti-cheat-sensitive games are not treated as safe by default just because a similar feature exists in NVIDIA App

## Phase 3 — Diagnostics and observability

Deliverables:

- execution logs
- launch plan snapshots
- mutation audit trail
- restore history
- record whether DLSS version selection or unsupported overrides were requested, applied, downgraded, ignored, or blocked

Definition of done:

- every apply/launch/restore action creates a traceable JSON record
- a failed run can be inspected without reproducing it immediately

## Phase 4 — Ecosystem expansion

Deliverables:

- Lutris adapter
- Heroic adapter
- import helpers for launcher metadata

Definition of done:

- external launcher metadata can be imported into the same `GameRecord` model
- launch plan generation remains launcher-agnostic in the core layer

## Phase 5 — UI and advanced features

Deliverables:

- desktop UI on top of the stable CLI/core modules
- optional database layer if JSON snapshots become limiting
- benchmark tooling
- optional profile sharing and trust labels

Definition of done:

- the UI is only a presentation layer over already-proven workflows
- core logic remains testable without the UI

---

## 8) Testing strategy by priority

## Must-have before Phase 1 is complete

- unit tests for profile parsing and validation
- unit tests for launch plan merge rules
- unit tests for wrapper order and env var generation
- unit tests for Steam launch-string generation
- unit tests for `dlss_version` and `allow_unsupported_override` validation

## Must-have before Phase 2 is complete

- unit tests for policy decisions
- table-driven tests for compatibility rules
- restore-path tests for Steam mutation rollback
- tests covering supported vs experimental vs blocked DLSS override paths
- tests covering valid and invalid DLSS version selection cases

## Must-have before Phase 3 is complete

- integration tests for preview -> apply -> restore flow
- execution result persistence tests
- failure-path tests for partially failing commands

---

## 9) Key design decisions

1. **CLI first, UI later**
   A stable CLI is the fastest way to validate the product model and safety workflows.

2. **JSON first, database later**
   JSON is sufficient for the current size of the project and keeps debugging simple.

3. **Safety before convenience**
   Anti-cheat and unsupported runtime combinations must be handled before broadening launcher support.

4. **Launcher-specific logic stays at the edges**
   The launch plan engine should not depend on Steam, Lutris, or Heroic internals.

5. **Preview and execution must share the same planner**
   There should not be separate logic for preview vs actual launch, otherwise drift is guaranteed.

6. **DLSS version selection is policy-driven, not best-effort magic**
   If the execution path cannot prove that a chosen DLSS runtime is supported, the plan should warn or block instead of pretending success.

7. **Unsupported-game override paths are experimental features**
   They should be modeled explicitly so logs, safety prompts, and tests can distinguish them from normal supported launches.

8. **Anti-cheat safety is title-specific, not feature-name-specific**
   Similarity to NVIDIA App behavior is not enough; protected titles need explicit verification before being treated as safe.

---

## 10) Immediate next implementation tasks

These are the next highest-value tasks for this repository:

1. Refactor `main.py` into `detector`, `profiles`, `games`, and `launch_plan` modules.
2. Define JSON validation rules for `GameRecord` and `Profile`.
3. Extend the profile and game schemas for `dlss_version`, `supports_dlss_version_selection`, and `allow_unsupported_override`.
4. Add tests for launch-plan generation, invalid input handling, and DLSS-specific policy cases.
5. Add a `launch` command with `--dry-run`.
6. Add Steam launch-option backup and restore with snapshot files.
7. Add a per-title anti-cheat policy table with conservative defaults and verification notes.

---

## 11) Sources used in earlier research

- NVIDIA App Smooth Motion overview:
  - https://www.nvidia.com/en-us/geforce/news/nvidia-app-global-dlss-overrides-rtx-40-series-smooth-motion/
- NVIDIA support article:
  - https://nvidia.custhelp.com/app/answers/detail/a_id/5621/~/enabling-smooth-motion-in-nvidia-app
- NVIDIA Linux README (Smooth Motion / nvpresent):
  - https://download.nvidia.com/XFree86/Linux-x86_64/575.57.08/README/nvpresent.html
- NVIDIA Linux application profiles docs:
  - https://download.nvidia.com/XFree86/Linux-x86_64/384.59/README/profiles.html
- Easy Anti-Cheat support article on modified game files:
  - https://www.easy.ac/support/articles/error-unknown-file-version
- BattlEye FAQ:
  - https://www.battleye.com/support/faq/
- NVIDIA Profile Inspector project (Windows context):
  - https://github.com/Orbmu2k/nvidiaProfileInspector/

---

## Bottom line

The original plan was technically directionally correct, but too ambitious for the actual state of the repository. The improved plan makes the first release concrete:

- stabilize the CLI core
- make launch mutation reversible
- add safety gating
- add diagnostics
- define DLSS version selection as an explicit, validated feature
- treat unsupported-game overrides as experimental policy-driven workflows
- require per-title anti-cheat verification instead of claiming universal NVIDIA-App-like safety
- only then expand to more launchers and UI
