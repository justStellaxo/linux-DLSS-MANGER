# Release Version Plan

Status: draft  
Date: 2026-04-17

## Goal

Ship the first release candidate of `DLLS Manager` as a usable, testable, CLI-first alpha release.

This release is not a broad end-user promise. It is a controlled alpha with:

- deterministic CLI behavior
- reversible apply/rollback flows
- conservative policy gating
- documented DLSS payload limitations
- repeatable local and CI test coverage

## Release Target

The release should be labeled as an alpha, for example:

- `v0.2.0-alpha.1` for the first release candidate
- `v0.2.0` after release-blocking issues are closed

Recommended positioning:

- Linux-only
- CLI-first
- advanced-user/testing release
- not a generic consumer UI app yet

## Current Baseline

Based on the current repository state, these parts already exist:

- CLI commands for discovery, validation, planning, apply, launch, rollback, profiles, and overrides
- discovery adapters for Steam, Faugus, Star Citizen LUG, Heroic, Lutris, Bottles, and desktop entries
- anti-cheat and DLSS policy evaluation
- mutation planning and rollback execution
- mock UI export
- GitHub Actions CI running the `unittest` suite

That means the release plan should focus less on inventing missing architecture and more on:

- stabilizing behavior
- narrowing supported scope
- hardening failure paths
- documenting safe usage
- defining release gates

## Release Scope

## In scope for the first release

- fully documented CLI workflow
- local install discovery and validation
- deterministic launch planning
- `prepare-launch`, `apply`, `launch`, and `rollback`
- snapshot and rollback records
- conservative anti-cheat gating
- install override persistence
- profile update persistence
- CI-backed automated regression tests

## Explicitly out of scope

- polished desktop UI
- automatic broad DLSS payload download/apply flow
- claiming title-by-title compatibility across all launchers
- mass-market packaging expectations
- anti-cheat bypass or unsafe override automation

## Release Workstreams

### 1. Product and support boundary

Before cutting a release, narrow the support statement.

Required decisions:

- define which launcher paths are officially supported in release notes
- define which adapters are experimental but shipped
- define whether `Heroic`, `Lutris`, and `Bottles` are release-grade or preview-only
- define whether downloaded DLSS payload management is deferred to the next version

Recommended first-release support policy:

- `Steam` and validated generic/script launch paths are primary
- `Faugus` and `Star Citizen LUG` are advanced-user paths
- `Heroic`, `Lutris`, `Bottles`, and generic desktop imports remain experimental until validated on real installs

### 2. Functional hardening

These are the highest-value implementation tasks before release:

1. Harden validation output for malformed installs and invalid metadata.
2. Ensure every mutation path is rollback-safe and produces a readable failure result.
3. Ensure blocked policies cannot be bypassed accidentally except through an explicit `--force` path.
4. Review dry-run behavior to make sure it never mutates files.
5. Ensure command previews, execution plans, and mutation plans stay aligned.
6. Tighten snapshot and rollback record consistency.

### 3. DLSS safety boundary

The release must document DLSS support conservatively.

Required state for this release:

- keep the current DLSS version list as metadata, not as a claim of universal safe swappability
- clearly document that payload catalog/download-manager work is next-phase, not release-complete
- do not imply that every selectable version is safe for every title/runtime path

### 4. Documentation and release UX

Before release, documentation must support a user running the tool end to end without reading source code.

Required docs:

- installation and setup
- quickstart
- safe workflow from discovery to rollback
- explanation of warnings, blocked states, and `--force`
- generated file locations
- known limitations
- supported versus experimental adapters

### 5. Packaging and reproducibility

The release artifact should be easy to install and retest.

Minimum packaging tasks:

- ensure `pip install -e .` works cleanly
- verify console entry point `dlls-manager`
- pin the supported Python range in docs and CI expectations
- add a release checklist for creating a Git tag and GitHub release notes

## Release Gates

The release is blocked until all of these are true.

### Gate A: Test suite

- full test suite passes locally
- full test suite passes in CI
- no flaky tests in two consecutive local runs

### Gate B: Core workflow verification

These manual flows must be verified on at least one real local install each where possible:

1. `discover-launchers`
2. `list-installs`
3. `show-install`
4. `validate-install`
5. `prepare-launch`
6. `apply`
7. `launch --dry-run`
8. `rollback`

### Gate C: Failure-path verification

These cases must be exercised before release:

- blocked anti-cheat policy returns a non-success result
- invalid install metadata produces readable validation errors
- rollback restores files after a successful apply
- failed apply does not silently leave partial state
- `launch --dry-run` does not mutate files
- `--force` behavior is visible and explicit in output

### Gate D: Documentation completeness

- `README.md` reflects actual current commands and workflow
- release limitations are written down
- experimental adapters are labeled clearly
- rollback and generated artifact locations are documented

## Test Strategy

The release test strategy should be divided into four layers.

### Layer 1: Schema and validation tests

Cover:

- `games.json`
- `profiles/*.json`
- anti-cheat rule data
- DLSS version metadata
- install override persistence

Goal:

- malformed data fails early and readably

### Layer 2: Unit and planner tests

Cover:

- effective profile merge logic
- env/wrapper generation
- compatibility and anti-cheat decisions
- mutation-plan construction
- execution-plan construction
- launch preview consistency

Goal:

- deterministic planning from static inputs

### Layer 3: Integration tests

Cover:

- CLI command output
- discovery cache lifecycle
- prepare -> apply -> rollback flow
- launch dry-run behavior
- install override persistence across commands

Goal:

- end-to-end CLI paths remain stable

### Layer 4: Manual real-install validation

Cover real systems for:

- one Steam title
- one script-based or non-Steam title
- one anti-cheat-sensitive title that should warn or block

Goal:

- catch launcher-specific and path-specific issues not visible in fixtures

## Manual Test Matrix

Recommended matrix for release signoff:

- `Steam` + safe profile + supported sample install
- `Steam` + experimental profile + blocked anti-cheat case
- `Faugus` + wrapper/import validation
- `Star Citizen LUG` + script execution plan validation
- `Heroic` + manifest import only
- `Lutris` + YAML import only
- `Bottles` + program discovery only

If some environments are unavailable, the release notes should say so explicitly and downgrade those adapters to experimental.

## CI Plan

Current CI runs the `unittest` suite on Ubuntu. That is a good base, but not the final release gate.

Recommended CI improvements before or immediately after first release:

- add a second job that installs with `.[dev]` if dev dependencies are introduced
- add `ruff check` once linting becomes enforced
- keep test execution non-interactive and deterministic
- ensure generated mock UI artifacts are not required for tests unless explicitly part of the scenario

## Release Checklist

Use this checklist before tagging a release.

1. Run the full automated test suite twice locally.
2. Run the documented quickstart from a fresh virtual environment.
3. Verify `dlls-manager --help`.
4. Execute the core manual workflow on real installs where available.
5. Review rollback output and generated artifacts.
6. Review `README.md` for accuracy.
7. Review release notes for known limits and experimental adapters.
8. Tag `v0.2.0-alpha.1` only after release blockers are closed.

## Known Release Risks

These risks should be called out rather than hidden.

- launcher ecosystem breadth is ahead of real-install validation depth
- DLSS version metadata exists before a full verified payload catalog exists
- anti-cheat safety decisions are conservative but still require title-level validation
- script and wrapper-based launchers may have environment-specific edge cases

## Definition Of Done For First Release

The first release is done when:

- automated tests pass locally and in CI
- the documented CLI workflow works end to end
- apply and rollback are demonstrably reversible
- experimental adapters are labeled honestly
- release notes and README match actual behavior
- no known release-blocking data-loss or silent-mutation bug remains open

## Immediate Next Tasks

1. Convert this release plan into an issue checklist or milestone.
2. Mark each adapter as `supported` or `experimental`.
3. Add missing failure-path tests for release blockers.
4. Run manual validation on real local installs and capture results.
5. Update release docs based on those validation results.
6. Cut `v0.2.0-alpha.1` only after the release gates are green.
