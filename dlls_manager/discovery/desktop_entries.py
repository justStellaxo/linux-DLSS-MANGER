from __future__ import annotations

import re
from pathlib import Path

from dlls_manager.discovery import base as discovery_base
from dlls_manager.discovery.base import build_install_id, normalize_path, parse_desktop_entry, parse_exec_command
from dlls_manager.models import LauncherInstallRecord


def _classify_command(command: list[str]) -> tuple[str, str]:
    if not command:
        return "desktop_exec", "desktop"
    target = command[0]
    if target.endswith(".sh"):
        return "script_exec", "desktop"
    if target.endswith(".desktop"):
        return "desktop_exec", "desktop"
    if target.endswith(".exe"):
        return "wine_exe", "vendor_prefix_launcher"
    return "native_exec", "native"


def _looks_like_game_entry(data: dict[str, str], command: list[str]) -> bool:
    categories = data.get("Categories", "").lower()
    if "game" in categories:
        return True

    combined = " ".join(
        [
            data.get("Name", ""),
            data.get("Comment", ""),
            data.get("Exec", ""),
            " ".join(command),
        ]
    ).lower()
    primary = command[0].lower() if command else ""

    keywords = (
        "game",
        "steam",
        "heroic",
        "lutris",
        "bottles",
        "battle.net",
        "battlenet",
        "blizzard",
        "wow",
        "warcraft",
        "star citizen",
        "rsi",
        "epic",
        "gog",
        "ubisoft",
        "ea app",
        "rockstar",
        "legendary",
    )
    if any(keyword in combined for keyword in keywords):
        return True

    script_markers = ("game", "launch", "wine", "steam", "heroic", "lutris", "bottle", "battle", "rsi", "citizen")
    if primary.endswith(".exe"):
        return True
    if primary.endswith(".sh"):
        return any(marker in combined for marker in script_markers)
    return False


def _extract_steam_app_id(command: list[str]) -> str | None:
    if not command:
        return None

    primary = Path(command[0]).name.lower()
    if "steam" not in primary:
        return None

    for index, token in enumerate(command[1:], start=1):
        if token == "-applaunch" and index + 1 < len(command):
            candidate = command[index + 1].strip()
            if candidate.isdigit():
                return candidate

        match = re.match(r"steam://rungameid/(\d+)", token, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def discover_desktop_entry_installations() -> list[LauncherInstallRecord]:
    if not discovery_base.LOCAL_APPLICATIONS_DIR.exists():
        return []

    installs: list[LauncherInstallRecord] = []
    for desktop_path in sorted(discovery_base.LOCAL_APPLICATIONS_DIR.glob("*.desktop")):
        data = parse_desktop_entry(desktop_path)
        exec_line = data.get("Exec")
        if not exec_line:
            continue
        if "faugus-run --game" in exec_line or "sc-launch.sh" in exec_line:
            continue

        wrappers, command = parse_exec_command(exec_line)
        if not _looks_like_game_entry(data, command):
            continue
        steam_app_id = _extract_steam_app_id(command)
        strategy, family = _classify_command(command)
        primary = command[0] if command else ""

        launch_command = command
        store_family = "generic"
        runtime = "native" if strategy == "native_exec" else "desktop"
        install_root = normalize_path(Path(primary).parent if primary.startswith("/") else None)
        exe_path = normalize_path(primary if primary.endswith(".exe") or primary.startswith("/") else None)
        working_directory = normalize_path(Path(primary).parent if primary.startswith("/") else None)
        scan_paths = [
            path
            for path in [
                normalize_path(Path(primary).parent if primary.startswith("/") else None),
                normalize_path(primary if primary.startswith("/") else None),
            ]
            if path
        ]
        notes = ["Imported from desktop entry discovery."]

        if steam_app_id:
            strategy = "steam_shortcut"
            family = "steam"
            store_family = "steam"
            runtime = "steam"
            launch_command = ["steam", "-applaunch", steam_app_id]
            install_root = None
            exe_path = None
            working_directory = None
            scan_paths = []
            notes = ["Imported from desktop entry discovery as a Steam shortcut."]

        installs.append(
            {
                "id": build_install_id("desktop_entry", desktop_path.stem),
                "display_name": data.get("Name", desktop_path.stem),
                "source": "desktop_entry",
                "source_id": desktop_path.stem,
                "launcher_family": family,  # type: ignore[typeddict-item]
                "store_family": store_family,  # type: ignore[typeddict-item]
                "execution_strategy": strategy,  # type: ignore[typeddict-item]
                "runtime": runtime,
                "install_root": install_root,
                "prefix_path": None,
                "runner_name": None,
                "runner_path": None,
                "exe_path": exe_path,
                "script_path": normalize_path(primary if primary.endswith(".sh") else None),
                "desktop_file": str(desktop_path),
                "app_id": steam_app_id,
                "launch_command": launch_command,
                "launch_env": {},
                "launch_args": "",
                "wrapper_chain": wrappers,
                "working_directory": working_directory,
                "scan_paths": scan_paths,
                "notes": notes,
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
