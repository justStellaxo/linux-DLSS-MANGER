from __future__ import annotations

from dlls_manager.game_db import load_games
from dlls_manager.models import LauncherInstallRecord


def discover_steam_installations() -> list[LauncherInstallRecord]:
    installs: list[LauncherInstallRecord] = []
    for game in load_games():
        if game["launcher"] != "steam":
            continue
        installs.append(
            {
                "id": f"steam:{game['id']}",
                "display_name": game["name"],
                "source": "steam",
                "source_id": game["id"],
                "launcher_family": "steam",
                "store_family": "steam",
                "execution_strategy": "steam_app",
                "runtime": game["runtime"],
                "install_root": game.get("scan_path"),
                "prefix_path": None,
                "runner_name": None,
                "runner_path": None,
                "exe_path": None,
                "script_path": None,
                "desktop_file": None,
                "app_id": game.get("app_id"),
                "launch_command": ["steam", "-applaunch", str(game.get("app_id"))] if game.get("app_id") else ["steam"],
                "launch_env": {},
                "launch_args": "",
                "wrapper_chain": [],
                "working_directory": None,
                "scan_paths": [path for path in [game.get("scan_path")] if path],
                "notes": list(game["notes"]),
                "validation_errors": [],
                "validation_warnings": [],
                "discovery_confidence": "medium",
                "anti_cheat": game["anti_cheat"],
                "anti_cheat_vendor": game["anti_cheat_vendor"],
                "anti_cheat_policy": game["anti_cheat_policy"],
                "supports_dlss_override": game["supports_dlss_override"],
                "supports_dlss_version_selection": game["supports_dlss_version_selection"],
                "override_mode": game["override_mode"],
            }
        )
    return installs
