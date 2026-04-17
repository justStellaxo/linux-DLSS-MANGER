from __future__ import annotations

import re
from pathlib import Path

from dlls_manager.discovery.base import build_install_id, normalize_path, parse_simple_yaml
from dlls_manager.models import LauncherInstallRecord
from dlls_manager.paths import LUTRIS_DIRS


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "lutris-game"


def _get_nested(data: dict[str, object], *keys: str) -> str | None:
    current: object = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    if current is None:
        return None
    value = str(current).strip()
    return value or None


def discover_lutris_installations() -> list[LauncherInstallRecord]:
    installs: list[LauncherInstallRecord] = []
    for root in LUTRIS_DIRS:
        games_dir = root / "games"
        if not games_dir.exists():
            continue

        for manifest_path in sorted([*games_dir.glob("*.yml"), *games_dir.glob("*.yaml")]):
            payload = parse_simple_yaml(manifest_path)
            display_name = (
                _get_nested(payload, "name")
                or _get_nested(payload, "game", "name")
                or manifest_path.stem
            )
            slug = _get_nested(payload, "game_slug") or _get_nested(payload, "slug") or _slugify(display_name)
            runner = _get_nested(payload, "runner") or "lutris"
            exe_path = normalize_path(_get_nested(payload, "game", "exe"))
            prefix_path = normalize_path(_get_nested(payload, "game", "prefix"))
            install_root = normalize_path(
                _get_nested(payload, "game", "directory")
                or _get_nested(payload, "game", "working_dir")
                or (Path(exe_path).parent if exe_path else None)
            )
            if not display_name:
                continue

            runner_name = _get_nested(payload, runner, "version") or runner
            installs.append(
                {
                    "id": build_install_id("lutris", slug),
                    "display_name": display_name,
                    "source": "lutris",
                    "source_id": slug,
                    "launcher_family": "lutris",
                    "store_family": "generic",
                    "execution_strategy": "lutris_game",
                    "runtime": f"lutris-{runner}",
                    "install_root": install_root,
                    "prefix_path": prefix_path,
                    "runner_name": runner_name,
                    "runner_path": None,
                    "exe_path": exe_path,
                    "script_path": normalize_path(exe_path if exe_path and exe_path.endswith(".sh") else None),
                    "desktop_file": None,
                    "app_id": None,
                    "launch_command": ["lutris", f"lutris:{slug}"],
                    "launch_env": {},
                    "launch_args": _get_nested(payload, "game", "args") or "",
                    "wrapper_chain": [],
                    "working_directory": install_root,
                    "scan_paths": [path for path in [install_root, prefix_path, exe_path] if path],
                    "notes": [f"Imported from Lutris game config: {manifest_path}"],
                    "validation_errors": [],
                    "validation_warnings": [],
                    "discovery_confidence": "medium",
                    "anti_cheat": "unknown",
                    "anti_cheat_vendor": None,
                    "anti_cheat_policy": "warn",
                    "supports_dlss_override": False,
                    "supports_dlss_version_selection": False,
                    "override_mode": "experimental",
                }
            )
    return installs
