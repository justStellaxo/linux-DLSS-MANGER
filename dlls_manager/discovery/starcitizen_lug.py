from __future__ import annotations

from pathlib import Path

from dlls_manager.discovery.base import build_install_id, find_matching_desktop_entry, normalize_path, parse_exec_command
from dlls_manager.models import LauncherInstallRecord
from dlls_manager.paths import STARCITIZEN_LUG_DIR


def _read_text(path: Path) -> str | None:
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8").strip()


def _extract_export(script_text: str, variable: str) -> str | None:
    prefix = f"export {variable}="
    for raw_line in script_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or not line.startswith(prefix):
            continue
        value = line[len(prefix) :].strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        return value or None
    return None


def _derive_runner_name(runner_bin: str | None) -> str | None:
    if not runner_bin:
        return None
    runner_path = Path(runner_bin)
    if runner_path.name == "bin":
        return runner_path.parent.name or runner_path.name
    if runner_path.parent.name == "bin":
        return runner_path.parent.parent.name or runner_path.parent.name
    return runner_path.name


def discover_starcitizen_lug_installations() -> list[LauncherInstallRecord]:
    game_dir = _read_text(STARCITIZEN_LUG_DIR / "gamedir.conf")
    wine_dir = _read_text(STARCITIZEN_LUG_DIR / "winedir.conf")
    if not game_dir and not wine_dir:
        return []

    desktop_path, desktop_data = find_matching_desktop_entry("sc-launch.sh", "RSI Launcher", "Star Citizen")
    wrappers: list[str] = []
    desktop_command: list[str] = []
    script_path: str | None = None
    if desktop_data and desktop_data.get("Exec"):
        wrappers, desktop_command = parse_exec_command(desktop_data["Exec"])
        if desktop_command:
            script_path = desktop_command[0]

    if not script_path and wine_dir:
        candidate = Path(wine_dir) / "sc-launch.sh"
        if candidate.exists():
            script_path = str(candidate)

    script_text = Path(script_path).read_text(encoding="utf-8") if script_path and Path(script_path).exists() else ""
    prefix_path = normalize_path(_extract_export(script_text, "WINEPREFIX") or wine_dir)
    runner_bin = normalize_path(_extract_export(script_text, "wine_path"))
    exe_path = None
    if prefix_path:
        candidate = Path(prefix_path) / "drive_c" / "Program Files" / "Roberts Space Industries" / "RSI Launcher" / "RSI Launcher.exe"
        exe_path = str(candidate)

    return [
        {
            "id": build_install_id("starcitizen_lug", "star-citizen"),
            "display_name": "Star Citizen",
            "source": "starcitizen_lug",
            "source_id": "star-citizen",
            "launcher_family": "rsi",
            "store_family": "rsi",
            "execution_strategy": "script_exec",
            "runtime": "wine-script",
            "install_root": normalize_path(game_dir),
            "prefix_path": prefix_path,
            "runner_name": _derive_runner_name(runner_bin),
            "runner_path": runner_bin,
            "exe_path": exe_path,
            "script_path": normalize_path(script_path),
            "desktop_file": normalize_path(desktop_path),
            "app_id": None,
            "launch_command": desktop_command or ([script_path] if script_path else []),
            "launch_env": {},
            "launch_args": "",
            "wrapper_chain": wrappers,
            "working_directory": prefix_path,
            "scan_paths": [path for path in [normalize_path(game_dir), prefix_path, exe_path] if path],
            "notes": [
                "Imported from Star Citizen LUG configuration.",
                "Launches through the LUG-maintained script and Wine runner.",
            ],
            "validation_errors": [],
            "validation_warnings": [],
            "discovery_confidence": "high",
            "anti_cheat": "unknown",
            "anti_cheat_vendor": None,
            "anti_cheat_policy": "warn",
            "supports_dlss_override": False,
            "supports_dlss_version_selection": False,
            "override_mode": "experimental",
        }
    ]
