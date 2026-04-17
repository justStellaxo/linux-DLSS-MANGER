from __future__ import annotations

from pathlib import Path

from dlls_manager.discovery.base import (
    build_install_id,
    find_matching_desktop_entry,
    normalize_path,
    parse_env_assignments,
    parse_exec_command,
)
from dlls_manager.models import LauncherInstallRecord
from dlls_manager.paths import FAUGUS_CONFIG_DIR, FAUGUS_GAMES_FILE
from dlls_manager.utils import load_json


def _load_global_env() -> dict[str, str]:
    path = FAUGUS_CONFIG_DIR / "envar.txt"
    if not path.exists():
        return {}
    env: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key] = value
    return env


def discover_faugus_installations() -> list[LauncherInstallRecord]:
    if not FAUGUS_GAMES_FILE.exists():
        return []
    payload = load_json(FAUGUS_GAMES_FILE)
    if not isinstance(payload, list):
        return []

    global_env = _load_global_env()
    installs: list[LauncherInstallRecord] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        game_id = str(item.get("gameid", "")).strip()
        if not game_id:
            continue

        desktop_path, desktop_data = find_matching_desktop_entry(f"faugus-run --game {game_id}", item.get("title", ""))
        wrappers: list[str] = []
        desktop_command: list[str] = []
        if desktop_data and desktop_data.get("Exec"):
            wrappers, desktop_command = parse_exec_command(desktop_data["Exec"])

        inline_env, _ = parse_env_assignments(str(item.get("launch_arguments", "")))
        validation_warnings: list[str] = []
        addapp_bat = item.get("addapp_bat")
        if addapp_bat and not Path(str(addapp_bat)).expanduser().exists():
            validation_warnings.append(f"Referenced addapp_bat does not exist: {addapp_bat}")

        installs.append(
            {
                "id": build_install_id("faugus", game_id),
                "display_name": str(item.get("title") or game_id),
                "source": "faugus",
                "source_id": game_id,
                "launcher_family": "umu",
                "store_family": "battle.net" if "battle" in game_id.lower() else "generic",
                "execution_strategy": "umu_game",
                "runtime": "umu-proton",
                "install_root": normalize_path(item.get("path")),
                "prefix_path": normalize_path(item.get("prefix")),
                "runner_name": str(item.get("runner") or ""),
                "runner_path": None,
                "exe_path": normalize_path(item.get("path")),
                "script_path": None,
                "desktop_file": normalize_path(desktop_path),
                "app_id": None,
                "launch_command": desktop_command or ["faugus-run", "--game", game_id],
                "launch_env": {**global_env, **inline_env},
                "launch_args": str(item.get("game_arguments") or ""),
                "wrapper_chain": wrappers,
                "working_directory": normalize_path(item.get("prefix")),
                "scan_paths": [
                    path
                    for path in [
                        normalize_path(item.get("prefix")),
                        normalize_path(Path(str(item.get("path", ""))).parent if item.get("path") else None),
                    ]
                    if path
                ],
                "notes": [
                    "Imported from Faugus launcher metadata.",
                    f"Lossless scaling enabled: {bool(item.get('lossless_enabled'))}",
                ],
                "validation_errors": [],
                "validation_warnings": validation_warnings,
                "discovery_confidence": "high",
                "anti_cheat": "unknown",
                "anti_cheat_vendor": None,
                "anti_cheat_policy": "warn",
                "supports_dlss_override": False,
                "supports_dlss_version_selection": False,
                "override_mode": "experimental",
            }
        )

    return installs
