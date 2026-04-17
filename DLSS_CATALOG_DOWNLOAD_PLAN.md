# DLSS Catalog And Download Manager Plan

Status: draft plan  
Date: 2026-04-17

## Goal

Add a production-safer DLSS payload catalog and a defensive download-manager layer to the project without pretending that every downloadable DLL on the internet is equally trustworthy.

The system should answer these questions:

- Which DLSS payload versions are known?
- Where did each payload come from?
- Is the source official, local, or a third-party mirror?
- Was the file hash verified?
- Was the file signature verified?
- Which payloads are allowed to be offered by default?
- Which games/runtimes are known to be compatible with a given payload family and version?

## What The Online Research Changes

The current project assumption should be tightened:

- Official NVIDIA developer releases do exist for DLSS and Streamline. They are suitable as first-class catalog sources.
- NVIDIA App also provides an official end-user update path for supported games, but that is not the same thing as a generic DLL download API.
- Community archives exist and can be useful as mirror sources, but they should not be treated as equivalent to official NVIDIA sources.

## Source Trust Model

The catalog should classify every source into one of these trust tiers.

### Tier 1: Official NVIDIA end-user path

Use case:

- game is supported by NVIDIA App DLSS overrides
- user wants the vendor-supported path instead of manual DLL swapping

How we treat it:

- track it as an official capability path
- do not model it as a generic downloadable DLL source inside the Linux tool
- use it as compatibility/reference metadata, not as the primary payload ingestion path

Why:

- NVIDIA App is an official update mechanism for supported titles
- it is not a public per-version file archive for this project to consume generically

### Tier 2: Official NVIDIA developer artifacts

Use case:

- build a canonical payload catalog from official NVIDIA developer releases

How we treat it:

- this should be the default enabled remote source class
- fetch release metadata from official NVIDIA GitHub releases and NVIDIA developer pages
- require pinned release URLs, file size, SHA-256, and signature verification before the payload becomes usable

Primary official sources:

- `https://github.com/NVIDIA/DLSS/releases`
- `https://github.com/NVIDIA-RTX/Streamline/releases`
- `https://developer.nvidia.com/rtx/dlss/get-started`
- `https://developer.nvidia.com/rtx/streamline/get-started`

### Tier 3: Local extraction from installed games

Use case:

- user already has trusted game installs on disk
- project wants to inventory existing local DLSS payloads

How we treat it:

- scan local game folders for known DLSS payload names
- hash and fingerprint each payload
- mark provenance as `local_extracted`
- never assume compatibility just because a file was found

This is important for Linux because local discovery is already a core project capability.

### Tier 4: Community mirrors

Use case:

- user explicitly wants versions not currently available via official channels
- user accepts mirror risk

How we treat it:

- disabled by default
- explicit opt-in only
- require both published checksums and local signature verification
- mark provenance as `community_mirror`
- never auto-apply mirrored payloads

Candidate mirrors:

- TechPowerUp DLSS DLL archive
- similar archives only after manual review

Important:

- mirrors can be useful, but they are still not NVIDIA-controlled primary distribution channels

## Recommended Product Position

The tool should not market itself as a generic "download random DLSS DLLs" utility.

It should position itself as:

- a catalog-driven DLSS payload manager
- official-source first
- local-source aware
- mirror-optional
- strict about provenance, hashing, signature checks, and rollback

## Proposed Data Model

Add a new catalog file such as `dlss_catalog.json`.

Each catalog entry should contain:

- `id`
- `family`
- `version`
- `display_label`
- `filename`
- `source_type`
- `source_name`
- `source_url`
- `release_url`
- `published_at`
- `file_size`
- `sha256`
- `signature_subject`
- `signature_status`
- `license_note`
- `redistribution_status`
- `supported_runtimes`
- `supported_arches`
- `compatibility_notes`
- `ingestion_method`
- `default_enabled`

Recommended enums:

- `family`: `super_resolution`, `frame_generation`, `ray_reconstruction`, `streamline_bundle`
- `source_type`: `official_vendor`, `official_developer`, `local_extracted`, `community_mirror`
- `signature_status`: `verified`, `missing`, `failed`, `unknown`
- `redistribution_status`: `allowed`, `restricted`, `unknown`

## Download Manager Architecture

Add a small provider-based subsystem, for example:

```text
dlls_manager/
├── dlss_catalog.py
├── dlss_sources.py
├── dlss_downloads.py
└── dlss_verify.py
```

Responsibilities:

- `dlss_catalog.py`
  - load and validate catalog metadata
  - merge static entries with fetched release metadata

- `dlss_sources.py`
  - define source providers
  - official GitHub/NVIDIA providers first
  - optional mirror providers behind an explicit flag

- `dlss_downloads.py`
  - download artifacts into a cache directory
  - persist provenance metadata and checksum manifests

- `dlss_verify.py`
  - verify SHA-256
  - verify PE signature where possible
  - normalize result into `verified`, `failed`, or `unknown`

Recommended storage:

```text
payloads/
└── dlss/
    ├── catalog.json
    ├── cache/
    └── manifests/
```

## CLI Plan

Add these commands in phases:

- `list-dlss-catalog`
- `show-dlss-version <id>`
- `sync-dlss-catalog`
- `download-dlss <id>`
- `verify-dlss-payload <path>`
- `import-local-dlss --path <game_dir>`

Important behavior rules:

- default downloads only from `official_vendor` or `official_developer`
- mirror downloads require `--allow-community-mirror`
- no download command should imply apply/swap
- apply must remain a separate explicit step with rollback support

## Verification Rules

Minimum acceptance rules for a payload to become selectable:

1. file download completed successfully
2. SHA-256 matches catalog metadata
3. filename matches expected payload family
4. provenance is recorded
5. signature verification succeeded, or the payload is explicitly downgraded to non-default status

Additional policy rules:

- a payload without hash must never be default-enabled
- a mirror payload without a valid local signature check must never be default-enabled
- a payload without compatibility metadata should remain download-only, not auto-recommended

## Compatibility Matrix Plan

The project should stop treating DLSS version choice as just a label list.

Instead, each version should eventually be classified against:

- payload family
- game/runtime path
- known launcher path
- anti-cheat sensitivity
- manual validation status

Suggested compatibility states:

- `verified_supported`
- `likely_supported`
- `experimental`
- `blocked`
- `unknown`

## Phased Implementation Plan

### Phase 1: Catalog hardening

- replace the current simple `dlss_versions.json` list with a richer catalog model
- add schema validation for provenance, hash, and source type
- seed the catalog with official NVIDIA DLSS and Streamline release metadata

### Phase 2: Verification pipeline

- add SHA-256 verification
- add file fingerprinting
- add optional PE signature verification support
- persist verification reports

### Phase 3: Download manager

- add official-source download providers
- add local cache management
- add resumable downloads and manifest files
- keep community mirrors disabled by default

### Phase 4: Local extraction

- scan discovered install paths for existing DLSS payloads
- import them into the local catalog as `local_extracted`
- surface duplicates and version drift

### Phase 5: Apply-path integration

- allow launch planning to reference catalog-backed payloads
- keep anti-cheat and compatibility gating in front of any mutation
- require rollback manifests for every applied payload swap

### Phase 6: UI integration

- expose catalog entries, provenance, verification state, and compatibility state in the future real UI
- keep download/apply as separate actions

## Security Rules

- Official sources only by default.
- Community mirrors must stay opt-in.
- Every downloaded payload must have a provenance record.
- Every applied payload must have a rollback path.
- The tool must never silently replace a game DLL just because a newer version exists.
- Anti-cheat-sensitive installs must remain blocked or warned by existing policy logic even if a payload is downloadable.

## Immediate Next Tasks

1. Introduce a new `dlss_catalog.json` schema and loader.
2. Keep `dlss_versions.json` only as a temporary compatibility layer or migrate it fully.
3. Add source-trust enums and validation tests.
4. Implement `list-dlss-catalog` and `show-dlss-version`.
5. Implement `sync-dlss-catalog` against official NVIDIA release metadata first.
6. Add checksum verification before any future apply path can use a downloaded payload.
7. Add optional mirror support only after the official pipeline is stable.

## Notes From Online Research

- NVIDIA states that DLSS 4.5 Super Resolution is available to NVIDIA App users and can be applied to over 400 games and apps through the NVIDIA App update path.
- NVIDIA's public DLSS GitHub repository exposes official SDK releases for developers, including versions such as `3.7.10`, `3.7.20`, and `310.x`.
- NVIDIA's Streamline documentation points developers to release zips for binary artifacts, and the Streamline repo explicitly warns to use original NVIDIA-signed DLLs or an equivalent signing system.
- TechPowerUp publishes checksums and states that its hosted DLLs are NVIDIA-signed, which makes it a reasonable optional mirror candidate, but still not an official NVIDIA primary source.

## Sources

- NVIDIA DLSS get started:
  - https://developer.nvidia.com/rtx/dlss/get-started
- NVIDIA DLSS GitHub releases:
  - https://github.com/NVIDIA/DLSS/releases
- NVIDIA DLSS GitHub repository:
  - https://github.com/NVIDIA/DLSS
- NVIDIA Streamline get started:
  - https://developer.nvidia.com/rtx/streamline/get-started
- NVIDIA Streamline GitHub repository:
  - https://github.com/NVIDIA-RTX/Streamline
- NVIDIA Streamline GitHub releases:
  - https://github.com/NVIDIA-RTX/Streamline/releases
- NVIDIA App DLSS 4.5 article:
  - https://www.nvidia.com/en-us/geforce/news/dlss-4-5-super-resolution-available-now/
- NVIDIA App global DLSS overrides article:
  - https://www.nvidia.com/en-us/geforce/news/gfecnt/20258/nvidia-app-global-dlss-overrides-rtx-40-series-smooth-motion/
- TechPowerUp DLSS archive article:
  - https://www.techpowerup.com/284182/techpowerup-hosts-nvidia-dlss-client-libraries
- TechPowerUp DLSS DLL archive:
  - https://www.techpowerup.com/download/nvidia-dlss-dll/
