# DLSS Manager

A Linux-native desktop app for managing DLSS versions, Proton launch options, and per-game overrides across Steam, Heroic, Lutris, Bottles, Faugus, and desktop entries.

Built with Python + PySide6 (Qt6). No web UI, no browser, no server — just a standalone app.

## Features

- **Library** — auto-discovers installed games across all launchers, shows anti-cheat status, DLSS support, release-support tier
- **Catalog** — browses official NVIDIA DLSS SDK releases (310.7.0), downloads SR + RR + FG DLLs
- **Profiles** — configure NVAPI, Smooth Motion, GameMode, MangoHud, HAGS, VKReflex, NGX Updater, DLSS preset overrides (J/K/L/M), PROTON_DLSS_UPGRADE
- **Rollbacks** — every mutation is reversible; automatic rollback on apply/launch failure
- **System** — detects GPU, Vulkan, Steam, MangoHud, GameMode, Gamescope availability

## Quick Start

```bash
git clone https://github.com/justStellaxo/linux-DLSS-MANGER.git
cd linux-DLSS-MANGER
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Launch the GUI:

```bash
dlls-manager-gui
```

Or use the CLI:

```bash
dlls-manager --help
```

## CLI Commands

```
detect                          Detect system capabilities
discover-launchers              Scan all launchers for game installs
list-installs                    List discovered installs
show-install <id>               Show install details
validate-install <id>           Validate an install
launch-preview <name|--id>       Preview launch command
explain-policy <name|--id>       Show policy evaluation
prepare-launch --install-id <id> Prepare launch plan
apply --install-id <id>          Apply DLSS mutations
launch --install-id <id>         Launch a game
list-rollbacks                   List rollback snapshots
rollback <id>                    Restore a rollback
refresh-dlss-catalog             Fetch latest DLSS releases from GitHub
list-dlss-catalog                List available DLSS versions
show-dlss-version <ver>          Show DLSS version details
download-dlss <ver>              Download and extract DLSS SDK
list-profiles                    List profiles
show-profile <name>              Show profile details
update-profile <name>            Update profile settings
show-install-override <id>      Show per-install override
update-install-override <id>    Update per-install override
```

## Typical Workflow

1. Discover and list installs:
```bash
dlls-manager discover-launchers
dlls-manager list-installs
```

2. Download a DLSS version:
```bash
dlls-manager refresh-dlss-catalog
dlls-manager list-dlss-catalog
dlls-manager download-dlss 310.7.0
```

3. Apply and launch:
```bash
dlls-manager apply --install-id steam:123456 --profile default
dlls-manager launch --install-id steam:123456 --profile default --dry-run
```

4. Roll back if needed:
```bash
dlls-manager list-rollbacks
dlls-manager rollback <rollback-id>
```

## GUI

The GUI has five pages accessible from the sidebar:

| Page | Description |
|------|-------------|
| Library | Game list with search, detail panel, command preview, override editor |
| Catalog | DLSS version table with SR/RR/FG availability and download buttons |
| Profiles | Profile editor with all DLSS/env-var toggles and preset dropdowns |
| Rollbacks | Rollback history table with restore action |
| System | OS, GPU, Vulkan, Steam, MangoHud, GameMode, Gamescope detection |

## DLSS Support

DLSS Manager tracks the 2026 DLSS landscape:

- **3 DLLs**: `nvngx_dlss.dll` (Super Resolution), `nvngx_dlssd.dll` (Ray Reconstruction), `nvngx_dlssg.dll` (Frame Generation)
- **Preset overrides**: J, K, L, M via `DXVK_NVAPI_DRS_SETTINGS`
- **Frame Generation on Linux**: `PROTON_ENABLE_NVAPI=1` + `WINEHAGS=1`
- **PROTON_DLSS_UPGRADE**: auto-upgrade or pin to specific version
- **NVIDIA Reflex**: `DXVK_NVAPI_VKREFLEX=1`
- **Smooth Motion**: `NVPRESENT_ENABLE_SMOOTH_MOTION=1`

## Launcher Support

| Launcher | Support Level |
|----------|--------------|
| Steam | advanced |
| Faugus | advanced |
| Star Citizen LUG | advanced |
| Heroic | experimental |
| Lutris | experimental |
| Bottles | experimental |
| Desktop entries | experimental |

## Testing

108 tests across three layers:

```bash
# Unit + smoke + E2E
python -m pytest tests/ tests_smoke/ tests_e2e/ -q
```

| Layer | Tests | What |
|-------|-------|------|
| Unit | 72 | Domain logic, catalog, presets, profiles, mutations, CLI |
| Smoke | 16 | Import checks, CLI commands, GUI launch |
| E2E | 20 | GUI navigation, library, catalog, profiles, system, rollbacks |

## Repository Layout

```
DLLS-Manager/
├── dlls_manager/
│   ├── gui/           PySide6 GUI (main_window, pages, workers, styles)
│   ├── discovery/     Launcher detection adapters
│   ├── execution/     Steam execution strategy
│   ├── mutations/      DLSS file mutation + rollback
│   ├── cli.py          CLI entry point
│   ├── launch_plan.py  Profile env-var + wrapper builder
│   ├── dlss_catalog.py DLSS catalog + download + extract
│   ├── detector.py     System capability detection
│   └── ...
├── profiles/           default, safe, experimental, minimal
├── tests/              Unit tests
├── tests_smoke/        Smoke tests
├── tests_e2e/          GUI E2E tests
└── pyproject.toml
```

## Safety Notes

- `launch --dry-run` resolves planning without mutating files
- If `apply` fails after partially changing files, automatic rollback runs immediately
- If `launch` fails to start after a successful `apply`, automatic rollback runs immediately
- Anti-cheat-sensitive titles are treated conservatively
- Unsupported-game overrides may be allowed, warned, ignored, or blocked depending on safety mode

## License

Alpha prototype. Not production-ready for broad deployment.