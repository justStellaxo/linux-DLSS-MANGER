from __future__ import annotations

import re
from pathlib import Path

from dlls_manager.discovery.base import build_install_id, normalize_path, parse_simple_yaml
from dlls_manager.models import LauncherInstallRecord
from dlls_manager.paths import BOTTLES_DIRS


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "bottle-program"


def _read_programs(bottle_dir: Path) -> list[tuple[str, str | None]]:
    programs_dir = bottle_dir / "programs"
    programs: list[tuple[str, str | None]] = []
    if not programs_dir.exists():
        return programs

    for program_file in sorted([*programs_dir.glob("*.yml"), *programs_dir.glob("*.yaml")]):
        payload = parse_simple_yaml(program_file)
        name = str(payload.get("name") or payload.get("Name") or program_file.stem).strip()
        exe_path = normalize_path(payload.get("path") or payload.get("executable") or payload.get("exe"))
        programs.append((name, exe_path))
    return programs


def discover_bottles_installations() -> list[LauncherInstallRecord]:
    installs: list[LauncherInstallRecord] = []
    for root in BOTTLES_DIRS:
        if not root.exists():
            continue

        for bottle_manifest in sorted(root.glob("**/bottle.yml")):
            bottle_dir = bottle_manifest.parent
            payload = parse_simple_yaml(bottle_manifest)
            bottle_name = str(payload.get("Name") or payload.get("name") or bottle_dir.name).strip()
            programs = _read_programs(bottle_dir)
            if not programs:
                programs = [(bottle_name, None)]

            for program_name, exe_path in programs:
                source_id = _slugify(f"{bottle_name}-{program_name}")
                install_root = normalize_path(Path(exe_path).parent if exe_path else bottle_dir)
                installs.append(
                    {
                        "id": build_install_id("bottles", source_id),
                        "display_name": program_name,
                        "source": "bottles",
                        "source_id": source_id,
                        "launcher_family": "bottles",
                        "store_family": "generic",
                        "execution_strategy": "bottles_program",
                        "runtime": "bottles-wine",
                        "install_root": install_root,
                        "prefix_path": normalize_path(bottle_dir),
                        "runner_name": str(payload.get("Runner") or payload.get("runner") or "bottles").strip(),
                        "runner_path": None,
                        "exe_path": exe_path,
                        "script_path": None,
                        "desktop_file": None,
                        "app_id": None,
                        "launch_command": ["bottles-cli", "run", "-b", bottle_name, "-p", program_name],
                        "launch_env": {},
                        "launch_args": "",
                        "wrapper_chain": [],
                        "working_directory": normalize_path(bottle_dir),
                        "scan_paths": [path for path in [install_root, normalize_path(bottle_dir), exe_path] if path],
                        "notes": [f"Imported from Bottles config: {bottle_manifest}"],
                        "validation_errors": [],
                        "validation_warnings": [],
                        "discovery_confidence": "medium" if exe_path else "low",
                        "anti_cheat": "unknown",
                        "anti_cheat_vendor": None,
                        "anti_cheat_policy": "warn",
                        "supports_dlss_override": False,
                        "supports_dlss_version_selection": False,
                        "override_mode": "experimental",
                    }
                )
    return installs
